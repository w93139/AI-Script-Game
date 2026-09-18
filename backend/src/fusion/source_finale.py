"""New public finale sources are selected, never reconstructed from model quotes."""
from copy import deepcopy

from pydantic import Field

from src.fusion.finale_evidence import FinaleAssessment
from src.fusion.located_evidence import SourceId, source_passage_index
from src.schemas.script_package import PackageModel

POLICY = 'finale-motivation/1.6'
OUTPUT_TOKENS = 1024


class SourceFinaleFact(PackageModel):
    source_id: SourceId
    point: str = Field(min_length=1, max_length=80, pattern=r'^\S(?:[\s\S]*\S)?$')


class SourceFinaleAssessment(FinaleAssessment):
    facts: list[SourceFinaleFact] = Field(max_length=3)


class SourceFinaleOutput(PackageModel):
    text: str = Field(max_length=60, pattern=r'^[^。！？!?；;\r\n]*[。！？!?]?$')
    assessment: SourceFinaleAssessment


def resolve_finale_sources(value, context):
    """Return exact selected source spans for private verification, not AI text."""
    index = source_passage_index(context)
    resolved = []
    seen = set()
    for fact in value['assessment']['facts']:
        span = index.get(fact['source_id'])
        if (span is None or span['collection'] == 'memory' or (fact['source_id'], fact['point']) in seen
                or not span['text'].strip() or not fact['point'].strip()):
            raise ValueError('FINALE_SOURCE_REFERENCE_INVALID')
        resolved.append(deepcopy(span))
        seen.add((fact['source_id'], fact['point']))
    return resolved


def validate_source_finale(value, context):
    parsed = SourceFinaleOutput.model_validate(value).model_dump()
    spans = resolve_finale_sources(parsed, context)
    # Reuse the frozen public wording/attribution/location checks, with sources
    # resolved from exact selected addresses. The model's text is never edited.
    from src.fusion.package_dialogue_model import validate_finale_motivation
    basis = list({(s['collection'], s['id']): {'collection': s['collection'], 'id': s['id']} for s in spans}.values())
    # Apply finite wording/location checks only to the selected spans. Keeping
    # the whole source here would allow an unselected paragraph to authorize a
    # location. Origin labels stay attached to the selected physical card.
    selected = deepcopy(context)
    for field in ('materials', 'discussion'):
        for item in selected[field]:
            collection = 'discussion' if field == 'discussion' else item['collection']
            item['text'] = '\n'.join(s['text'] for s in spans
                                     if s['collection'] == collection and s['id'] == item['id'])
    selected['schema_version'] = 'finale-motivation-context/1.4'
    validate_finale_motivation({'text': parsed['text'], 'basis': basis}, selected)
    a = parsed['assessment']
    if a['relation'] == 'UNKNOWN':
        if (parsed['text'] or spans or a['exclusive']
                or any(a[k] != 'UNKNOWN' for k in ('event_relation', 'time_relation', 'identity_relation'))):
            raise ValueError('FINALE_SOURCE_UNKNOWN_INVALID')
    elif not parsed['text'] or not spans:
        raise ValueError('FINALE_SOURCE_FACT_REQUIRED')
    if a['relation'] == 'CONFLICT':
        same = a['event_relation'] == 'SAME' and a['time_relation'] == 'OVERLAP'
        persistent = a['event_relation'] in ('SAME', 'DIFFERENT') and a['time_relation'] == 'PERSISTENT_FACT'
        if len(spans) < 2 or not (same or persistent) or a['identity_relation'] != 'SAME' or not a['exclusive']:
            raise ValueError('FINALE_SOURCE_CONFLICT_UNSUPPORTED')
    elif a['exclusive']:
        raise ValueError('FINALE_SOURCE_EXCLUSIVITY_INVALID')
    if a['relation'] == 'POSSIBLE_LINK' and len(spans) < 2:
        raise ValueError('FINALE_SOURCE_LINK_REQUIRES_TWO_FACTS')
    return parsed


def source_finale_schema(context):
    schema = SourceFinaleOutput.model_json_schema()
    refs = [key for key, span in source_passage_index(context).items()
            if span['collection'] != 'memory' and span['text'].strip()]
    schema['$defs']['SourceFinaleFact']['properties']['source_id'] = {'type': 'string', **({'enum': refs} if refs else {})}
    # State the same compatibility checks in the sent schema, not only prose or
    # server validation. These labels still do not prove semantic entailment.
    base = schema['$defs']['SourceFinaleAssessment']
    variants = []
    for relation, event, time in [('OBSERVATION', None, None), ('POSSIBLE_LINK', None, None),
                                  ('CONFLICT', ['SAME'], ['OVERLAP']),
                                  ('CONFLICT', ['SAME', 'DIFFERENT'], ['PERSISTENT_FACT']),
                                  ('UNKNOWN', ['UNKNOWN'], ['UNKNOWN'])]:
        branch = deepcopy(base); props = branch['properties']
        props['facts']['uniqueItems'] = True
        props['relation'] = {'const': relation}
        props['exclusive'] = {'const': relation == 'CONFLICT'}
        if event: props['event_relation'] = {'enum': event}
        if time: props['time_relation'] = {'enum': time}
        if relation == 'UNKNOWN':
            props['identity_relation'] = {'const': 'UNKNOWN'}
            props['facts']['maxItems'] = 0
        else:
            props['facts']['minItems'] = 1 if relation == 'OBSERVATION' else 2
            if not refs: continue
            if relation == 'CONFLICT': props['identity_relation'] = {'const': 'SAME'}
        variants.append(branch)
    schema['$defs']['SourceFinaleAssessment'] = {'anyOf': variants}
    schema['anyOf'] = [
        {'properties': {'text': {'const': ''},
                        'assessment': {'properties': {'relation': {'const': 'UNKNOWN'}}}}},
        {'properties': {'text': {'minLength': 1},
                        'assessment': {'properties': {'relation': {'enum': ['OBSERVATION', 'POSSIBLE_LINK', 'CONFLICT']}}}}},
    ]
    return schema

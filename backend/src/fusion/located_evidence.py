"""Source-addressed evidence for new policies only; no semantic repair.

A selected address always expands to that source, never a source guessed from
model wording. Short physical cards stay whole, including their instructions.
"""
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from src.fusion.table_evidence import (
    EvidenceSelection, EvidenceAnswer, EvidenceReflection, EvidenceAssessment,
    _lossless_passages, evidence_output_schema,
)

SOURCE_POLICY = 'source-addressed-lossless-passages/1.0'
SourceId = Annotated[str, StringConstraints(
    pattern=r'^[kemd]:[A-Za-z0-9][A-Za-z0-9._:-]*/p[1-9][0-9]*$', max_length=160)]


def source_wire_context(context):
    wire = deepcopy(context)
    for field in ('materials', 'discussion'):
        for item in wire[field]:
            text = item.pop('text')
            prefix = ('d' if field == 'discussion' else
                      {'knowledge': 'k', 'evidence': 'e', 'memory': 'm'}[item['collection']])
            address = f"{prefix}:{item['id']}"
            if field == 'materials' and item['collection'] == 'evidence' and len(text) <= 1200:
                passages = [{'id': address + '/p1', 'text': text}]
            else:
                passages = [{'id': f'{address}/p{n}', 'text': span['text']}
                            for n, span in enumerate(_lossless_passages(text, 'unused'), 1)]
            item['passages'] = passages
    return wire


def source_passage_index(context):
    wire = source_wire_context(context)
    result = {}
    for field in ('materials', 'discussion'):
        for item in wire[field]:
            attrs = {k: v for k, v in item.items() if k != 'passages'}
            if field == 'discussion': attrs['collection'] = 'discussion'
            for span in item['passages']:
                if span['id'] in result:
                    raise ValueError('SOURCE_ADDRESS_DUPLICATE')
                result[span['id']] = {**attrs, 'passage_id': span['id'], 'text': span['text']}
    return result


class SourceEvidenceSelection(EvidenceSelection):
    basis: list[SourceId] = Field(min_length=1, max_length=3)


class SourceEvidenceAnswer(EvidenceAnswer):
    selections: list[SourceEvidenceSelection] = Field(max_length=10)


class SourceEvidenceReflection(EvidenceReflection):
    basis: list[SourceId] = Field(max_length=3)


class SourceEvidenceAssessment(EvidenceAssessment):
    schema_version: Literal['table-evidence-assessment/1.1']
    answers: list[SourceEvidenceAnswer] = Field(min_length=1, max_length=100)
    reflection: SourceEvidenceReflection


def source_evidence_projection(output, context):
    if context['action'] != 'SEAL_FINALE':
        raise ValueError('TABLE_EVIDENCE_ACTION_INVALID')
    parsed = SourceEvidenceAssessment.model_validate(output).model_dump()
    allowed = {key for key, span in source_passage_index(context).items() if span['text'].strip()}
    for item in [*(s for a in parsed['answers'] for s in a['selections']), parsed['reflection']]:
        refs = item['basis']
        if len(refs) != len(set(refs)) or not set(refs) <= allowed:
            raise ValueError('TABLE_EVIDENCE_REFERENCE_INVALID')
    reflection = parsed['reflection']
    text = ('推测：' if reflection['certainty'] == 'INFERRED' else '') + reflection['text']
    decision = {'schema_version': 'structured-finale-submission/1.0',
                'answers': [{'question_id': a['question_id'], 'option_ids': [s['option_id'] for s in a['selections']]}
                            for a in parsed['answers']],
                'vote': deepcopy(parsed['vote']), 'reflection': text}
    return decision, parsed


def source_evidence_output_schema(context):
    # Reuse the unchanged per-question choice/limit branches, replacing only
    # the new contract's source addresses and assessment version. This does not
    # change the old schema helper or any previous prepared payload.
    schema = evidence_output_schema(context)
    schema['title'] = 'SourceEvidenceAssessment'
    schema['properties']['schema_version']['const'] = 'table-evidence-assessment/1.1'
    refs = [key for key, span in source_passage_index(context).items() if span['text'].strip()]
    schema['$defs']['EvidenceBasis']['items'] = {'type': 'string', **({'enum': refs} if refs else {})}
    return schema


def authorized_evidence_origins(engine, materials):
    """Only visible physical cards and completed direct release actions.

    An action's prerequisites are not discovery locations and are not traversed.
    This projection must run before the context is frozen and is never inferred
    from model text, package truth, scoring, or an unacquired card.
    """
    completed = set(engine.state()['completed_action_ids'])
    labels = {a['id']: a['label'] for a in engine._package['mechanics']['actions']
              if a['id'] in completed}
    visible = {m['id'] for m in materials if m['collection'] == 'evidence'}
    return [{'id': m['id'], 'labels': list(dict.fromkeys(labels[a]
                for a in m['release'].get('required_action_ids', []) if a in labels))}
            for m in engine._package['evidence'] if m['id'] in visible]

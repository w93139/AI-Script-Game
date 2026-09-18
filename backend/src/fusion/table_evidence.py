"""Private, finite decision evidence; reference integrity is not entailment proof.

Only caller-authorized context is accepted. Source spans preserve every character,
including whitespace, and never infer ungranted memories from other catalogues.
"""
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from src.fusion.speech_passages import source_passages
from src.schemas.package_primitives import PackageModel, StableId
from src.schemas.table_decisions import FinaleVote

EVIDENCE_POLICY = 'table-evidence/1.0'
PASSAGE_POLICY = 'lossless-source-passages/1.0'
ASSESSMENT_VERSION = 'table-evidence-assessment/1.0'
PassageId = Annotated[str, StringConstraints(pattern=r'^[md][0-9]{4,}\.p[0-9]{4,}$', max_length=32)]
Certainty = Literal['DIRECT', 'INFERRED', 'UNKNOWN']


def _lossless_passages(text, prefix):
    # source_passages fixes the semantic boundaries. Attach its whitespace gaps
    # to adjacent spans instead of dropping them or transmitting text twice.
    spans = source_passages(text)
    if not spans:
        return [{'id': prefix + '.p0001', 'text': text}]
    return [{'id': prefix + '.' + span['id'],
             'text': text[0 if i == 0 else span['start']:
                          spans[i + 1]['start'] if i + 1 < len(spans) else len(text)]}
            for i, span in enumerate(spans)]


def evidence_wire_context(context):
    """Copy context, replacing source text with globally named lossless passages."""
    wire = deepcopy(context)
    for field, prefix in (('materials', 'm'), ('discussion', 'd')):
        for n, item in enumerate(wire[field], 1):
            item['passages'] = _lossless_passages(item.pop('text'), f'{prefix}{n:04d}')
    return wire


def evidence_passage_index(context):
    """Short ID -> original source identity, attributes and exact visible span."""
    wire = evidence_wire_context(context)
    result = {}
    for field in ('materials', 'discussion'):
        for item in wire[field]:
            attributes = {k: v for k, v in item.items() if k != 'passages'}
            if field == 'discussion':
                attributes['collection'] = 'discussion'
            for passage in item['passages']:
                result[passage['id']] = {**attributes, 'passage_id': passage['id'], 'text': passage['text']}
    return result


class EvidenceSelection(PackageModel):
    option_id: StableId
    certainty: Literal['DIRECT', 'INFERRED']
    basis: list[PassageId] = Field(min_length=1, max_length=3)
    summary: str = Field(min_length=1, max_length=48)

    @model_validator(mode='after')
    def bounded_decision(self):
        if not self.summary.strip():
            raise ValueError('TABLE_SELECTED_EVIDENCE_REQUIRED')
        return self


class EvidenceAnswer(PackageModel):
    question_id: StableId
    # No selection explicitly means UNKNOWN; partial supported selections are
    # allowed, without claiming all other options have been proved false.
    selections: list[EvidenceSelection] = Field(max_length=10)


class EvidenceReflection(PackageModel):
    text: str = Field(max_length=120)
    certainty: Certainty
    basis: list[PassageId] = Field(max_length=3)

    @model_validator(mode='after')
    def bounded_reflection(self):
        if self.certainty == 'UNKNOWN':
            if self.text or self.basis:
                raise ValueError('TABLE_UNKNOWN_HAS_CONCLUSION')
        elif not self.text.strip() or not self.basis:
            raise ValueError('TABLE_REFLECTION_EVIDENCE_REQUIRED')
        return self


class EvidenceAssessment(PackageModel):
    schema_version: Literal['table-evidence-assessment/1.0']
    answers: list[EvidenceAnswer] = Field(min_length=1, max_length=100)
    vote: FinaleVote
    reflection: EvidenceReflection


def evidence_projection(output, context):
    """Validate source existence and posture, then strip private evidence fields.

The table adapter additionally checks all question options, coverage and votes.
DIRECT/INFERRED is the model's assessment, never a server entailment verdict.
"""
    if context['action'] != 'SEAL_FINALE':
        raise ValueError('TABLE_EVIDENCE_ACTION_INVALID')
    parsed = EvidenceAssessment.model_validate(output).model_dump()
    index = evidence_passage_index(context)
    allowed = {key for key, span in index.items() if span['text'].strip()}
    for item in [*(s for a in parsed['answers'] for s in a['selections']), parsed['reflection']]:
        refs = item['basis']
        if len(refs) != len(set(refs)) or not set(refs) <= allowed:
            raise ValueError('TABLE_EVIDENCE_REFERENCE_INVALID')
    reflection = parsed['reflection']
    # Preserve an explicit uncertainty marker after the private assessment is
    # stripped. This label adds no case facts and never changes selected options.
    text = ('推测：' if reflection['certainty'] == 'INFERRED' else '') + reflection['text']
    decision = {'schema_version': 'structured-finale-submission/1.0',
                'answers': [{'question_id': a['question_id'], 'option_ids': [s['option_id'] for s in a['selections']]}
                            for a in parsed['answers']],
                'vote': deepcopy(parsed['vote']), 'reflection': text}
    return decision, parsed


def evidence_output_schema(context):
    """Compact per-question branches plus a shared, visible-passage reference enum."""
    schema = EvidenceAssessment.model_json_schema()
    defs = schema['$defs']
    refs = [key for key, span in evidence_passage_index(context).items() if span['text'].strip()]
    basis = {'type': 'array', 'minItems': 1, 'maxItems': 3,
             'items': {'type': 'string', **({'enum': refs} if refs else {})}}
    # No visible source means no supported choice. Empty selections stay legal.
    groups = {}
    for q in context['questions']:
        key = (tuple(sorted(o['id'] for o in q['options'])), q['max_choices'])
        groups.setdefault(key, []).append(q['id'])
    branches = []
    defs['EvidenceBasis'] = basis
    defs.pop('EvidenceSelection')
    for (options, limit), questions in groups.items():
        selection = {'type': 'object', 'properties': {
            'option_id': {'type': 'string', **({'enum': list(options)} if options else {})},
            'certainty': {'enum': ['DIRECT', 'INFERRED']},
            'basis': {'$ref': '#/$defs/EvidenceBasis'},
            'summary': {'type': 'string', 'minLength': 1, 'maxLength': 48}},
            'additionalProperties': False}
        branches.append({'type': 'object', 'properties': {
            'question_id': {'type': 'string', 'enum': questions},
            'selections': {'type': 'array', 'maxItems': limit if refs else 0, 'items': selection}},
            'additionalProperties': False})
    defs['EvidenceAnswer'] = {'anyOf': branches}
    unknown_reflection = {'type': 'object', 'properties': {
        'text': {'const': ''}, 'certainty': {'const': 'UNKNOWN'},
        'basis': {'type': 'array', 'maxItems': 0, 'items': {'type': 'string'}}},
        'additionalProperties': False}
    supported_reflection = {'type': 'object', 'properties': {
        'text': {'type': 'string', 'minLength': 1, 'maxLength': 120},
        'certainty': {'enum': ['DIRECT', 'INFERRED']},
        'basis': {'$ref': '#/$defs/EvidenceBasis'}}, 'additionalProperties': False}
    defs['EvidenceReflection'] = {'anyOf': [unknown_reflection, *([supported_reflection] if refs else [])]}
    vote = defs['FinaleVote']['properties']
    vote['accusation_id'] = {'enum': [None, *(o['id'] for o in context['accusation_options'])]}
    vote['trust_character_id'] = {'enum': [None, *context['trust_character_ids']]}
    schema['properties']['answers'].update(minItems=len(context['questions']), maxItems=len(context['questions']))
    return schema

"""Opt-in, authored response sections over already authorized source passages."""
from copy import deepcopy
from typing import Literal
import unicodedata

from pydantic import Field, field_validator, model_validator

from src.schemas.package_primitives import PackageModel, StableId
from src.fusion.speech_passages import source_passages


PLAN_POLICY = 'topic-response-plan/1.0'


class TopicPlanBasis(PackageModel):
    collection: Literal['knowledge', 'evidence', 'memory']
    id: StableId
    passage_ids: list[StableId] = Field(min_length=1, max_length=6)

    @model_validator(mode='after')
    def unique_passages(self):
        if len(set(self.passage_ids)) != len(self.passage_ids):
            raise ValueError('TOPIC_RESPONSE_PLAN_PASSAGES_INVALID')
        return self


def _instruction(value):
    if not value.strip() or any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs')
                                and c not in '\n\t' for c in value):
        raise ValueError('TOPIC_RESPONSE_PLAN_INSTRUCTION_INVALID')
    return value


class TopicResponseSection(PackageModel):
    id: StableId
    mode: Literal['REPORT', 'INFERENCE']
    instruction: str = Field(min_length=1, max_length=600)
    basis: list[TopicPlanBasis] = Field(min_length=1, max_length=3)

    _valid_instruction = field_validator('instruction')(_instruction)

    @model_validator(mode='after')
    def unique_basis(self):
        if len({(ref.collection, ref.id) for ref in self.basis}) != len(self.basis):
            raise ValueError('TOPIC_RESPONSE_PLAN_BASIS_INVALID')
        return self


class TopicResponsePlan(PackageModel):
    schema_version: Literal['topic-response-plan/1.0']
    instruction: str = Field(min_length=1, max_length=1200)
    sections: list[TopicResponseSection] = Field(min_length=1, max_length=3)

    _valid_instruction = field_validator('instruction')(_instruction)

    @model_validator(mode='after')
    def unique_sections(self):
        if len({section.id for section in self.sections}) != len(self.sections):
            raise ValueError('TOPIC_RESPONSE_PLAN_SECTIONS_INVALID')
        return self


def validate_topic_plan(plan, materials):
    """Validate references against caller-authorized full text, without granting it."""
    parsed = TopicResponsePlan.model_validate(plan).model_dump()
    for section in parsed['sections']:
        for ref in section['basis']:
            material = materials.get((ref['collection'], ref['id']))
            if material is None:
                raise ValueError('TOPIC_RESPONSE_PLAN_SOURCE_UNAUTHORIZED')
            known = {passage['id'] for passage in source_passages(material['text'])}
            if not set(ref['passage_ids']) <= known:
                raise ValueError('TOPIC_RESPONSE_PLAN_PASSAGES_INVALID')
    return parsed


def project_topic_wire(wire, source_context):
    """Select original passages for this task; full audit input is never rewritten."""
    projected = deepcopy(wire)
    task = source_context.get('topic_response_task')
    if task is None:
        return projected
    sources = {(m['collection'], m['id']): m for m in source_context['materials']}
    plan = validate_topic_plan(task, sources)
    allowed = {}
    for section in plan['sections']:
        for ref in section['basis']:
            allowed.setdefault((ref['collection'], ref['id']), set()).update(ref['passage_ids'])
    retained = []
    for material in projected['materials']:
        key = (material['collection'], material['id'])
        if key not in allowed:
            continue
        original = {p['id']: p['text'] for p in source_passages(sources[key]['text'])}
        passages = [p for p in material['passages'] if p['id'] in allowed[key]]
        if (len(passages) != len(allowed[key]) or {p['id'] for p in passages} != allowed[key]
                or any(p['text'] != original[p['id']] for p in passages)):
            raise ValueError('TOPIC_RESPONSE_PLAN_WIRE_INVALID')
        material['passages'] = passages
        retained.append(material)
    if (len(retained) != len(allowed)
            or {(m['collection'], m['id']) for m in retained} != set(allowed)):
        raise ValueError('TOPIC_RESPONSE_PLAN_WIRE_INVALID')
    projected['materials'] = retained
    projected['strategy_materials'] = []
    target = [d for d in projected['discussion'] if d['id'] == source_context['reply_to']]
    if len(target) != 1:
        raise ValueError('TOPIC_RESPONSE_PLAN_TARGET_INVALID')
    window = projected.setdefault('history_window', {'policy': 'full-play-context-window/1.0', 'omitted_count': 0})
    window['omitted_count'] += len(projected['discussion']) - len(target)
    projected['discussion'] = target
    return projected


def _basis_set(refs):
    keys = [(r['collection'], r['id']) for r in refs]
    if (len(keys) != len(set(keys)) or any(not r['passage_ids']
            or len(r['passage_ids']) != len(set(r['passage_ids'])) for r in refs)):
        raise ValueError('TOPIC_RESPONSE_PLAN_OUTPUT_INVALID')
    return {(r['collection'], r['id'], frozenset(r['passage_ids'])) for r in refs}


def validate_topic_plan_output(speech, context):
    """Reject a divergent response; never fill in omitted references or prose."""
    task = context.get('topic_response_task')
    if task is None:
        return
    plan = validate_topic_plan(task, {(m['collection'], m['id']): m for m in context['materials']})
    segments = speech['segments']
    # Existing speech validation owns the exact unknown-only representation.
    if len(segments) == 1 and segments[0]['mode'] == 'UNCERTAIN':
        return
    if len(segments) != len(plan['sections']):
        raise ValueError('TOPIC_RESPONSE_PLAN_OUTPUT_INVALID')
    for segment, section in zip(segments, plan['sections']):
        if (segment['mode'] != section['mode']
                or _basis_set(segment['basis']) != _basis_set(section['basis'])):
            raise ValueError('TOPIC_RESPONSE_PLAN_OUTPUT_INVALID')

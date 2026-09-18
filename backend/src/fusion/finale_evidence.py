"""Bounded public-statement evidence, retained privately for source review.

Exact excerpts and reference integrity are checked here. Relationship labels are
model assertions, not automatic proof of entailment or of a player's guilt.
"""
from typing import Literal

from pydantic import Field

from src.fusion.table_evidence import PassageId, evidence_passage_index
from src.schemas.script_package import PackageModel

POLICY = 'finale-motivation/1.5'
OUTPUT_TOKENS = 1024


class FinaleFact(PackageModel):
    passage_id: PassageId
    excerpt: str = Field(min_length=1, max_length=240)


class FinaleAssessment(PackageModel):
    facts: list[FinaleFact] = Field(max_length=3)
    relation: Literal['OBSERVATION', 'POSSIBLE_LINK', 'CONFLICT', 'UNKNOWN']
    event_relation: Literal['SAME', 'DIFFERENT', 'UNKNOWN']
    time_relation: Literal['OVERLAP', 'SEQUENCE', 'PERSISTENT_FACT', 'UNKNOWN']
    identity_relation: Literal['SAME', 'SIMILAR', 'UNKNOWN']
    exclusive: bool


def validate_finale_assessment(result, context):
    assessment = FinaleAssessment.model_validate(result['assessment']).model_dump()
    facts = assessment['facts']
    index = evidence_passage_index(context)
    refs = set()
    seen = set()
    for fact in facts:
        span = index.get(fact['passage_id'])
        key = (fact['passage_id'], fact['excerpt'])
        if (span is None or not fact['excerpt'].strip() or fact['excerpt'] not in span['text']
                or key in seen or span['collection'] == 'memory'):
            raise ValueError('FINALE_EVIDENCE_EXCERPT_INVALID')
        seen.add(key)
        refs.add((span['collection'], span['id']))
    if refs != {(ref['collection'], ref['id']) for ref in result['basis']}:
        raise ValueError('FINALE_EVIDENCE_BASIS_MISMATCH')
    if assessment['relation'] == 'UNKNOWN':
        if (result['text'] or facts or assessment['exclusive']
                or any(assessment[key] != 'UNKNOWN' for key in
                       ('event_relation', 'time_relation', 'identity_relation'))):
            raise ValueError('FINALE_EVIDENCE_UNKNOWN_INVALID')
    elif not result['text'] or not facts:
        raise ValueError('FINALE_EVIDENCE_FACT_REQUIRED')
    if assessment['relation'] == 'CONFLICT':
        same_moment = assessment['event_relation'] == 'SAME' and assessment['time_relation'] == 'OVERLAP'
        persistent = assessment['event_relation'] in ('SAME', 'DIFFERENT') and assessment['time_relation'] == 'PERSISTENT_FACT'
        if (len(facts) < 2 or not (same_moment or persistent)
                or assessment['identity_relation'] != 'SAME' or not assessment['exclusive']):
            raise ValueError('FINALE_EVIDENCE_CONFLICT_UNSUPPORTED')
    elif assessment['exclusive']:
        raise ValueError('FINALE_EVIDENCE_EXCLUSIVITY_INVALID')
    if assessment['relation'] == 'POSSIBLE_LINK' and len(facts) < 2:
        raise ValueError('FINALE_EVIDENCE_LINK_REQUIRES_TWO_FACTS')
    return assessment

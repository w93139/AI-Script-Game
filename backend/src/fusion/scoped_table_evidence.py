"""Complete selected wording is auditable; it is not an entailment oracle."""
from copy import deepcopy
from typing import Literal

from pydantic import Field

from src.fusion.located_evidence import (
    SourceEvidenceSelection, SourceEvidenceAnswer, SourceEvidenceAssessment,
    source_evidence_projection, source_evidence_output_schema,
)

ASSESSMENT_VERSION = 'table-evidence-assessment/1.2'
OPTION_TEXT_POLICY = 'complete-selected-option-text/1.0'


class ScopedEvidenceSelection(SourceEvidenceSelection):
    option_text: str = Field(min_length=1, max_length=2000)


class ScopedEvidenceAnswer(SourceEvidenceAnswer):
    selections: list[ScopedEvidenceSelection] = Field(max_length=10)


class ScopedEvidenceAssessment(SourceEvidenceAssessment):
    schema_version: Literal['table-evidence-assessment/1.2']
    answers: list[ScopedEvidenceAnswer] = Field(min_length=1, max_length=100)


def scoped_evidence_projection(value, context):
    parsed = ScopedEvidenceAssessment.model_validate(value).model_dump()
    questions = {q['id']: {o['id']: o['label'] for o in q['options']} for q in context['questions']}
    for answer in parsed['answers']:
        options = questions.get(answer['question_id'], {})
        for selection in answer['selections']:
            if options.get(selection['option_id']) != selection['option_text']:
                raise ValueError('TABLE_SELECTED_OPTION_TEXT_MISMATCH')
    # Projection drops only the redundant copied label; it never substitutes a
    # choice, source, certainty, summary or reflection in the model receipt.
    prior = deepcopy(parsed)
    prior['schema_version'] = 'table-evidence-assessment/1.1'
    for answer in prior['answers']:
        for selection in answer['selections']:
            del selection['option_text']
    decision, _ = source_evidence_projection(prior, context)
    return decision, parsed


def scoped_evidence_output_schema(context):
    schema = source_evidence_output_schema(context)
    schema['title'] = 'ScopedEvidenceAssessment'
    schema['properties']['schema_version']['const'] = ASSESSMENT_VERSION
    # Labels remain in the complete question context. Enforce the exact
    # (question, id, text) pairing on receipt without duplicating all labels
    # in the schema and consuming the authorized source budget.
    for branch in schema['$defs']['EvidenceAnswer']['anyOf']:
        selection = branch['properties']['selections']['items']
        selection['properties']['option_text'] = {
            'type': 'string', 'minLength': 1, 'maxLength': 2000}
    # JSON Schema titles carry no validation semantics. New-policy-only
    # compaction keeps room for authorized sources in providers that repeat
    # the response schema in their system message.
    def without_titles(value):
        if isinstance(value, dict):
            return {key: without_titles(item) for key, item in value.items() if key != 'title'}
        if isinstance(value, list):
            return [without_titles(item) for item in value]
        return value
    return without_titles(schema)

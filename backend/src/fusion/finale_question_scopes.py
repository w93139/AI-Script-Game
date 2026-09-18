"""Versioned, authored question wording over currently authorized knowledge.

This checks scope and source integrity, not whether the authored wording is a
sound clarification. It never derives answers, changes choices, or grants text.
"""
from copy import deepcopy
from hashlib import sha256
from typing import Literal
import unicodedata

from pydantic import Field, field_validator, model_validator

from src.fusion.package_validation import content_hash
from src.schemas.package_primitives import Digest, PackageModel, StableId

SCOPES_POLICY = 'finale-question-scopes/1.0'


def _text_hash(text):
    if type(text) is not str:
        raise ValueError('FINALE_QUESTION_SCOPES_TEXT_INVALID')
    return sha256(text.encode('utf-8')).hexdigest()


class ScopeBasis(PackageModel):
    collection: Literal['knowledge']
    id: StableId
    text_sha256: Digest


class ScopeQuestion(PackageModel):
    question_id: StableId
    original_prompt_sha256: Digest
    prompt: str = Field(min_length=1, max_length=800)
    basis: list[ScopeBasis] = Field(min_length=1, max_length=6)

    @field_validator('prompt')
    @classmethod
    def safe_prompt(cls, value):
        if not value.strip() or any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs')
                                    and c not in '\n\t' for c in value):
            raise ValueError('FINALE_QUESTION_SCOPES_PROMPT_INVALID')
        return value

    @model_validator(mode='after')
    def unique_basis(self):
        if len({ref.id for ref in self.basis}) != len(self.basis):
            raise ValueError('FINALE_QUESTION_SCOPES_BASIS_DUPLICATE')
        return self


class _ScopeDocument(PackageModel):
    schema_version: Literal['finale-question-scopes/1.0']
    package_hash: Digest
    character_id: StableId
    questions: list[ScopeQuestion] = Field(min_length=1, max_length=100)


def _unique_index(items, key, error):
    result = {}
    for item in items:
        identifier = key(item)
        if identifier in result:
            raise ValueError(error)
        result[identifier] = item
    return result


class FinaleQuestionScopes:
    """Validate a server-owned document against its unchanged source package."""

    def __init__(self, package, document):
        parsed = _ScopeDocument.model_validate(document).model_dump()
        if parsed['package_hash'] != content_hash(package):
            raise ValueError('FINALE_QUESTION_SCOPES_PACKAGE_MISMATCH')
        actor = parsed['character_id']
        if actor not in {c['id'] for c in package['characters']}:
            raise ValueError('FINALE_QUESTION_SCOPES_CHARACTER_INVALID')
        questions = _unique_index(package['full_play']['finale']['questions'],
                                  lambda q: q['id'], 'FINALE_QUESTION_SCOPES_QUESTION_DUPLICATE')
        knowledge = _unique_index(package['knowledge'], lambda m: m['id'],
                                  'FINALE_QUESTION_SCOPES_SOURCE_DUPLICATE')
        _unique_index(parsed['questions'], lambda q: q['question_id'],
                      'FINALE_QUESTION_SCOPES_QUESTION_DUPLICATE')
        for scope in parsed['questions']:
            question = questions.get(scope['question_id'])
            if question is None or question['character_id'] != actor:
                raise ValueError('FINALE_QUESTION_SCOPES_QUESTION_UNAUTHORIZED')
            if _text_hash(question['prompt']) != scope['original_prompt_sha256']:
                raise ValueError('FINALE_QUESTION_SCOPES_PROMPT_MISMATCH')
            for ref in scope['basis']:
                source = knowledge.get(ref['id'])
                if source is None or not (
                    source['visibility'] == 'PUBLIC' and source['character_id'] is None
                    or source['visibility'] == 'CHARACTER_PRIVATE' and source['character_id'] == actor
                ):
                    raise ValueError('FINALE_QUESTION_SCOPES_SOURCE_UNAUTHORIZED')
                if _text_hash(source['text']) != ref['text_sha256']:
                    raise ValueError('FINALE_QUESTION_SCOPES_SOURCE_MISMATCH')
        self.package_hash = parsed['package_hash']
        self.character_id = actor
        self.revision = content_hash(parsed)
        self._document = deepcopy(parsed)

    def freeze(self):
        return deepcopy(self._document)


def available_scopes(questions, materials, scopes):
    """Project validated scopes using caller-authorized materials only.

    A missing basis defers the entire clarification. A present but changed
    source or original question is an integrity failure, never a silent skip.
    The caller binds the validated document to the current package and actor.
    """
    if type(scopes) is not list:
        raise ValueError('FINALE_QUESTION_SCOPES_LIST_INVALID')
    parsed = [ScopeQuestion.model_validate(scope).model_dump() for scope in scopes]
    _unique_index(parsed, lambda q: q['question_id'], 'FINALE_QUESTION_SCOPES_QUESTION_DUPLICATE')
    question_index = _unique_index(questions, lambda q: q['id'],
                                   'FINALE_QUESTION_SCOPES_QUESTION_DUPLICATE')
    source_index = _unique_index(materials, lambda m: (m['collection'], m['id']),
                                 'FINALE_QUESTION_SCOPES_SOURCE_DUPLICATE')
    result = []
    for scope in parsed:
        question = question_index.get(scope['question_id'])
        if question is None or _text_hash(question['prompt']) != scope['original_prompt_sha256']:
            raise ValueError('FINALE_QUESTION_SCOPES_PROMPT_MISMATCH')
        acquired = True
        for ref in scope['basis']:
            source = source_index.get((ref['collection'], ref['id']))
            if source is None:
                acquired = False
            elif _text_hash(source['text']) != ref['text_sha256']:
                raise ValueError('FINALE_QUESTION_SCOPES_SOURCE_MISMATCH')
        if acquired:
            result.append(scope)
    return deepcopy(result)


def apply_scopes(questions, materials, scopes):
    """Return the same authorized questions and choices, changing only prompts."""
    available = {scope['question_id']: scope['prompt']
                 for scope in available_scopes(questions, materials, scopes)}
    result = deepcopy(questions)
    for question in result:
        if question['id'] in available:
            question['prompt'] = available[question['id']]
    return result

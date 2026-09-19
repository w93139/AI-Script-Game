"""Opt-in reasoning: exact wire, independent counters, no exposed thought text."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.fusion.package_role_model import PackageRoleModelError
from src.fusion.package_table_model import (
    BoundedScopedPackageTableModel, ScopedPackageTableModel, BOUNDED_MODEL_CONTRACT,
    table_context_window,
)
from src.fusion.package_validation import canonical_json
from src.services.llm_service import LLMResponse
from tests.fusion_security.test_bound_table_model import settings as old_settings, context
from tests.fusion_security.test_scoped_table_policy import scoped_context, assessment


def settings(**kw):
    return replace(old_settings(), provider='aliyun_bailian',
                   model='qwen3.7-flash-2026-07-15', **kw)


def response(c=None, *, completion=200, reasoning=50, text=True):
    details = {'reasoning_tokens': reasoning}
    if text:
        details['text_tokens'] = completion  # Inclusive, per Bailian's contract.
    return LLMResponse(content=canonical_json(assessment(c or scoped_context())),
        model=settings().model, finish_reason='stop', reasoning_content='PRIVATE_THOUGHT_SENTINEL',
        usage={'prompt_tokens': 100, 'completion_tokens': completion,
               'completion_tokens_details': details, 'total_tokens': 100 + completion})


def invoke(result, c=None):
    sdk = SimpleNamespace(chat_completion=AsyncMock(return_value=result))
    model = BoundedScopedPackageTableModel(sdk, settings())
    prepared = model.prepare(c or scoped_context())
    return asyncio.run(model.call(prepared)), sdk, model, prepared


def test_exact_seal_wire_preserves_sources_and_total_not_independent_answer_cap():
    c = scoped_context(); c['discussion'] = []
    model = BoundedScopedPackageTableModel(object(), settings())
    p = model.prepare(c); old = ScopedPackageTableModel(object(), settings()).prepare(c)
    assert p['messages'] == old['messages']
    assert p['source_context'] == c and p['wire_context_hash'] == old['wire_context_hash']
    assert p['params']['max_completion_tokens'] == 5120
    assert p['params']['stream'] is False
    assert p['params']['extra_body'] == {'enable_thinking': True, 'preserve_thinking': False,
                                       'enable_search': False, 'thinking_budget': 1024}
    assert 'max_tokens' not in p['params']
    assert p['output_tokens'] == model.metadata()['reserved_output_tokens'] == 5136
    assert p['reasoning_policy']['answer_acceptance_limit'] == 4096
    assert model.metadata()['schema_version'] == BOUNDED_MODEL_CONTRACT
    size = len(canonical_json(p['messages']).encode()) + len(canonical_json(p['params']['response_format']).encode())
    assert table_context_window(c, size, BOUNDED_MODEL_CONTRACT) == c
    with pytest.raises(ValueError):
        table_context_window(c, size - 1, BOUNDED_MODEL_CONTRACT)


@pytest.mark.parametrize('text', [True, False])
def test_reasoning_subset_success_is_billed_once_and_never_returned(text):
    result, sdk, _, _ = invoke(response(text=text))
    assert result['status'] == 'OK' and sdk.chat_completion.await_count == 1
    assert result['usage']['completion_tokens'] == 200 and result['usage']['reasoning_tokens'] == 50
    assert result['assessment'] == assessment(scoped_context())
    assert 'PRIVATE_THOUGHT_SENTINEL' not in canonical_json(result)


@pytest.mark.parametrize('change,error', [
    ('missing', 'FINALE_REASONING_USAGE_INVALID'),
    ('reasoning-over', 'FINALE_REASONING_LIMIT_EXCEEDED'),
    ('answer-over', 'FINALE_REASONING_ANSWER_LIMIT_EXCEEDED'),
    ('old-text-semantics', 'FINALE_REASONING_USAGE_INVALID'),
    ('truncated', 'PACKAGE_ROLE_OUTPUT_TRUNCATED'),
    ('wrong-model', 'PACKAGE_ROLE_MODEL_MISMATCH'),
])
def test_bad_reasoning_or_answer_is_not_repaired_and_retains_known_usage(change, error):
    r = response()
    if change == 'missing':
        r.usage['completion_tokens_details'].pop('reasoning_tokens')
    elif change == 'reasoning-over':
        r = response(completion=1100, reasoning=1025)
    elif change == 'answer-over':
        r = response(completion=4100, reasoning=0)
    elif change == 'old-text-semantics':
        r.usage['completion_tokens_details']['text_tokens'] = 150
    elif change == 'truncated':
        r.finish_reason = 'length'
    else:
        r.model = 'another-model'
    result, sdk, _, _ = invoke(r)
    assert result['status'] == 'INVALID' and result['error_code'] == error
    assert result['usage']['completion_tokens'] == r.usage['completion_tokens']
    assert 'assessment' not in result and 'decision' not in result
    assert sdk.chat_completion.await_count == 1


def test_missing_usage_stays_unknown_without_second_dispatch():
    r = response(); r.usage = None
    result, sdk, _, _ = invoke(r)
    assert result['status'] == 'UNKNOWN' and result['usage'] is None
    assert sdk.chat_completion.await_count == 1


def test_nonempty_thought_with_zero_reasoning_is_invalid_but_billed_once():
    result, sdk, _, _ = invoke(response(reasoning=0))
    assert result['status'] == 'INVALID'
    assert result['error_code'] == 'FINALE_REASONING_USAGE_MISMATCH'
    assert result['usage']['completion_tokens'] == 200
    assert sdk.chat_completion.await_count == 1


def test_non_seal_cannot_spend_the_unused_reasoning_allowance_on_its_answer():
    c = context(); c.update(action='CAST_BALLOT', options=[dict(id='go', label='院子', cost=1)],
                            questions=[], accusation_options=[], trust_character_ids=[])
    r = response(completion=4200, reasoning=0); r.reasoning_content = None
    result, _, _, _ = invoke(r, c)
    assert result['error_code'] == 'PACKAGE_ROLE_USAGE_EXCEEDS_RESERVATION'
    assert result['usage']['completion_tokens'] == 4200


@pytest.mark.parametrize('field', ['reasoning_policy', 'output_tokens', 'params', 'source_context'])
def test_tampered_frozen_request_never_dispatches(field):
    sdk = SimpleNamespace(chat_completion=AsyncMock(return_value=response()))
    model = BoundedScopedPackageTableModel(sdk, settings()); p = model.prepare(scoped_context())
    if field == 'params': p[field]['extra_body']['thinking_budget'] = 2048
    elif field == 'source_context': p[field]['materials'][0]['text'] += ' new content'
    elif field == 'output_tokens': p[field] += 1
    else: p[field]['reasoning_limit'] = 2048
    result = asyncio.run(model.call(p))
    assert result['model_attempted'] is False and sdk.chat_completion.await_count == 0


def test_other_provider_cannot_silently_enable_reasoning():
    sdk = SimpleNamespace(chat_completion=AsyncMock())
    model = BoundedScopedPackageTableModel(sdk, old_settings())
    assert not model.available and model.metadata()['reasoning_policy'] is None
    with pytest.raises(PackageRoleModelError, match='PROVIDER_UNSUPPORTED'):
        model.prepare(scoped_context())
    assert sdk.chat_completion.await_count == 0


@pytest.mark.parametrize('action', ['CAST_BALLOT', 'BREAK_TIE'])
def test_non_seal_keeps_old_disabled_request_params(action):
    c = context(); c.update(action=action, options=[dict(id='go', label='院子', cost=1)],
                            questions=[], accusation_options=[], trust_character_ids=[])
    model = BoundedScopedPackageTableModel(object(), settings())
    p = model.prepare(c); old = ScopedPackageTableModel(object(), settings()).prepare(c)
    assert p['params'] == old['params'] and p['messages'] == old['messages']
    assert p['params']['extra_body']['enable_thinking'] is False
    assert p['output_tokens'] == 5136  # Conservative shared policy, no extra generation.


def test_old_adapter_still_rejects_reasoning_and_cannot_resume_new_request():
    sdk = SimpleNamespace(chat_completion=AsyncMock(return_value=response(text=False)))
    old = ScopedPackageTableModel(sdk, settings())
    assert asyncio.run(old.call(old.prepare(scoped_context())))['error_code'] == 'PACKAGE_ROLE_REASONING_FORBIDDEN'
    prepared = BoundedScopedPackageTableModel(sdk, settings()).prepare(scoped_context())
    assert asyncio.run(old.call(prepared))['model_attempted'] is False
    assert sdk.chat_completion.await_count == 1

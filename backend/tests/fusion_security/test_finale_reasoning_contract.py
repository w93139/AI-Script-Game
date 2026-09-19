"""Synthetic receipts for the independent bounded seal reasoning contract."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest

from src.fusion.budget import normalize_provider_usage
from src.fusion.finale_reasoning import (
    ENDPOINT_FINGERPRINT, MODEL, PROVIDER, PROVIDER_CONTRACT,
    REASONING_POLICY_VERSION, REASONING_TOKENS, normalize_reasoning_usage,
    reasoning_policy, reasoning_usage_error, require_reasoning_base,
    require_reasoning_budget,
)


def usage(completion=1400, reasoning=1000, text=True):
    details = {'reasoning_tokens': reasoning}
    if text:
        details['text_tokens'] = completion
    return {'prompt_tokens': 100, 'completion_tokens': completion,
            'total_tokens': 100 + completion, 'completion_tokens_details': details}


def base():
    return {'provider': PROVIDER, 'model': MODEL, 'provider_contract': PROVIDER_CONTRACT,
            'endpoint_fingerprint': ENDPOINT_FINGERPRINT, 'thinking_mode': 'disabled'}


@pytest.mark.parametrize('limit', [64, 1000, 4096])
def test_policy_separates_requested_total_reserved_total_and_answer_admission(limit):
    p = reasoning_policy(limit)
    assert p['schema_version'] == REASONING_POLICY_VERSION
    assert p['action'] == 'SEAL_FINALE'
    assert p['reasoning_limit'] == REASONING_TOKENS == 1024
    assert p['answer_acceptance_limit'] == limit
    assert p['max_completion_tokens'] == limit + 1024
    assert p['reservation_tolerance'] == 16
    assert p['reserved_output_tokens'] == limit + 1040
    p['reasoning_limit'] = 999999
    assert reasoning_policy(limit)['reasoning_limit'] == 1024


@pytest.mark.parametrize('value', [True, False, None, '1000', 1000.0, 63, 4097, -1])
def test_invalid_answer_limit_never_coerced(value):
    with pytest.raises(ValueError, match='ANSWER_LIMIT_INVALID'):
        reasoning_policy(value)


def test_exact_disabled_base_is_required_without_mutation():
    b = base(); original = deepcopy(b)
    assert require_reasoning_base(b) is None
    assert b == original
    for field in b:
        wrong = {**b, field: 'other'}
        with pytest.raises(ValueError, match='BASE_UNSUPPORTED'):
            require_reasoning_base(wrong)
        missing = dict(b); del missing[field]
        with pytest.raises(ValueError, match='BASE_UNSUPPORTED'):
            require_reasoning_base(missing)
    for wrong in (None, [], 'provider'):
        with pytest.raises(ValueError):
            require_reasoning_base(wrong)


def test_conservative_input_tier_budget_is_bound_and_does_not_mutate():
    snapshot = {'input_rate_cny': '0.6', 'cached_input_rate_cny': '0.6', 'output_rate_cny': '2.4'}
    original = deepcopy(snapshot)
    assert require_reasoning_budget(snapshot) is None
    assert snapshot == original
    assert require_reasoning_budget({key: Decimal('12') for key in snapshot}) is None
    policy = reasoning_policy(4096)
    assert policy['minimum_input_rate_cny'] == policy['minimum_cached_input_rate_cny'] == '0.6'
    assert policy['minimum_output_rate_cny'] == '2.4'
    assert policy['pricing_basis_version']


@pytest.mark.parametrize('field', ['input_rate_cny', 'cached_input_rate_cny', 'output_rate_cny'])
@pytest.mark.parametrize('bad', [None, True, False, 'NaN', 'Infinity', '-1', 'n/a', {}, [], '0.2'])
def test_low_tier_invalid_or_missing_rates_cannot_enable_new_reasoning(field, bad):
    snapshot = {'input_rate_cny': '0.6', 'cached_input_rate_cny': '0.6', 'output_rate_cny': '2.4'}
    snapshot[field] = bad
    with pytest.raises(ValueError, match='BUDGET_UNSUPPORTED'):
        require_reasoning_budget(snapshot)
    del snapshot[field]
    with pytest.raises(ValueError, match='BUDGET_UNSUPPORTED'):
        require_reasoning_budget(snapshot)


@pytest.mark.parametrize('snapshot', [None, [], 'rates'])
def test_budget_snapshot_must_be_mapping(snapshot):
    with pytest.raises(ValueError, match='BUDGET_UNSUPPORTED'):
        require_reasoning_budget(snapshot)


@pytest.mark.parametrize('text', [False, True])
def test_reasoning_is_a_subset_not_a_second_completion_charge(text):
    raw = usage(text=text); before = deepcopy(raw)
    result = normalize_reasoning_usage(raw)
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 1400
    assert result.reasoning_tokens == 1000
    assert result.total_tokens == 1500
    assert reasoning_usage_error(raw, result, 400) is None
    assert raw == before
    if text:
        assert normalize_provider_usage(raw) is None  # old contract remains unchanged


@pytest.mark.parametrize('reasoning,answer', [(0, 64), (1024, 64), (1024, 4096)])
def test_receipt_limits_include_both_closed_boundaries(reasoning, answer):
    raw = usage(reasoning + answer, reasoning)
    assert reasoning_usage_error(raw, normalize_reasoning_usage(raw), answer) is None


@pytest.mark.parametrize('completion,reasoning,answer,error', [
    (1089, 1025, 64, 'FINALE_REASONING_LIMIT_EXCEEDED'),
    (1089, 1024, 64, 'FINALE_REASONING_ANSWER_LIMIT_EXCEEDED'),
    (65, 0, 64, 'FINALE_REASONING_ANSWER_LIMIT_EXCEEDED'),
    (5130, 1024, 4096, 'FINALE_REASONING_ANSWER_LIMIT_EXCEEDED'),
])
def test_reservation_tolerance_does_not_relax_answer_or_reasoning_admission(completion, reasoning, answer, error):
    raw = usage(completion, reasoning)
    assert reasoning_usage_error(raw, normalize_reasoning_usage(raw), answer) == error


@pytest.mark.parametrize('value', [None, True, False, -1, 1000.0, '1000', 1401])
def test_malformed_reasoning_cannot_be_zero_or_exceed_completion(value):
    raw = usage(); raw['completion_tokens_details']['reasoning_tokens'] = value
    assert normalize_reasoning_usage(raw) is None


@pytest.mark.parametrize('field', ['prompt_tokens', 'completion_tokens', 'total_tokens'])
@pytest.mark.parametrize('value', [True, False, -1, '100', 100.0, None])
def test_totals_are_strict_integers(field, value):
    raw = usage(); raw[field] = value
    assert normalize_reasoning_usage(raw) is None


@pytest.mark.parametrize('details', [None, {}, {'text_tokens': 1400}, {'reasoning_tokens': 1000, 'text_tokens': 400},
    {'reasoning_tokens': 1000, 'text_tokens': True}, {'reasoning_tokens': 1000, 'audio_tokens': 0}])
def test_missing_or_contradictory_breakdowns_rejected(details):
    raw = usage(); raw['completion_tokens_details'] = details
    before = deepcopy(raw)
    assert normalize_reasoning_usage(raw) is None
    assert reasoning_usage_error(raw, normalize_provider_usage(raw), 4096) == 'FINALE_REASONING_USAGE_INVALID'
    assert raw == before


def test_missing_reasoning_can_account_via_old_normalizer_but_never_admit_answer():
    raw = usage(); del raw['completion_tokens_details']
    fallback = normalize_provider_usage(raw)
    assert fallback.completion_tokens == 1400 and fallback.reasoning_tokens == 0
    assert normalize_reasoning_usage(raw) is None
    assert reasoning_usage_error(raw, fallback, 4096) == 'FINALE_REASONING_USAGE_INVALID'


def test_cache_and_total_consistency_preserved_and_input_immutable():
    raw = usage(); raw['prompt_tokens_details'] = {'cached_tokens': 25, 'text_tokens': 100}
    raw['cached_prompt_tokens'] = 25
    before = deepcopy(raw)
    assert normalize_reasoning_usage(raw).cached_prompt_tokens == 25
    assert raw == before
    raw['cached_prompt_tokens'] = 26
    assert normalize_reasoning_usage(raw) is None
    raw = usage(); raw['total_tokens'] += 1
    assert normalize_reasoning_usage(raw) is None


@pytest.mark.parametrize('details', [{'audio_tokens': 0}, {'text_tokens': 99}, {'text_tokens': True},
                                  {'cached_tokens': True}, {'cached_tokens': 101}])
def test_pure_text_prompt_breakdown_must_match_total(details):
    raw = usage(); raw['prompt_tokens_details'] = details
    assert normalize_reasoning_usage(raw) is None


def test_admission_revalidates_raw_even_with_accounting_fallback_or_forged_normalized():
    raw = usage(); result = normalize_reasoning_usage(raw)
    for field in ('prompt_tokens', 'completion_tokens', 'cached_prompt_tokens', 'reasoning_tokens'):
        altered = replace(result, **{field: getattr(result, field) + 1})
        assert reasoning_usage_error(raw, altered, 4096) == 'FINALE_REASONING_USAGE_MISMATCH'
    assert reasoning_usage_error(raw, None, 4096) == 'FINALE_REASONING_USAGE_MISMATCH'
    assert reasoning_usage_error(raw, replace(result, cost_cny=Decimal('0.1')), 4096) is None

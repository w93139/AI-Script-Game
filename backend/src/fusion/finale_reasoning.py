"""Opt-in Bailian seal reasoning limits; no global provider or usage changes.

For this exact pure-text contract, completion text includes reasoning. The
reasoning count is a subset of completion, never an additional billable total.
"""
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from hashlib import sha256

from src.fusion.budget import UsageAmount, normalize_provider_usage


REASONING_POLICY_VERSION = 'bounded-seal-reasoning/1.0'
REASONING_TOKENS = 1024
RESERVATION_TOLERANCE = 16
PROVIDER = 'aliyun_bailian'
MODEL = 'qwen3.7-flash-2026-07-15'
PROVIDER_CONTRACT = 'bailian-chat-qwen37-v2'
USAGE_CONTRACT = 'bailian-pure-text-reasoning-subset/1.0'
PRICING_BASIS_VERSION = 'BAILIAN_QWEN37_FLASH_32K_256K_20260920'
MIN_INPUT_RATE = Decimal('0.6')
MIN_OUTPUT_RATE = Decimal('2.4')
ENDPOINT = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
ENDPOINT_FINGERPRINT = sha256(ENDPOINT.encode()).hexdigest()


def reasoning_policy(answer_limit):
    """Return a fresh policy; the visible-answer limit is a receipt constraint."""
    if type(answer_limit) is not int or not 64 <= answer_limit <= 4096:
        raise ValueError('FINALE_REASONING_ANSWER_LIMIT_INVALID')
    total = answer_limit + REASONING_TOKENS
    return {
        'schema_version': REASONING_POLICY_VERSION,
        'action': 'SEAL_FINALE',
        'provider': PROVIDER,
        'model': MODEL,
        'provider_contract': PROVIDER_CONTRACT,
        'usage_contract': USAGE_CONTRACT,
        'pricing_basis_version': PRICING_BASIS_VERSION,
        'minimum_input_rate_cny': str(MIN_INPUT_RATE),
        'minimum_cached_input_rate_cny': str(MIN_INPUT_RATE),
        'minimum_output_rate_cny': str(MIN_OUTPUT_RATE),
        'reasoning_limit': REASONING_TOKENS,
        'answer_acceptance_limit': answer_limit,
        'max_completion_tokens': total,
        'reservation_tolerance': RESERVATION_TOLERANCE,
        'reserved_output_tokens': total + RESERVATION_TOLERANCE,
    }


def require_reasoning_base(base):
    """Require the exact frozen disabled base before a seal-only opt-in."""
    expected = {
        'provider': PROVIDER, 'model': MODEL,
        'provider_contract': PROVIDER_CONTRACT,
        'endpoint_fingerprint': ENDPOINT_FINGERPRINT,
        'thinking_mode': 'disabled',
    }
    if not isinstance(base, Mapping) or any(base.get(k) != v for k, v in expected.items()):
        raise ValueError('FINALE_REASONING_BASE_UNSUPPORTED')


def require_reasoning_budget(snapshot):
    """Require conservative rates for the entire allowed input reservation.

98,304 input bytes plus the 4,096 token envelope reach the 32K–256K tier.
Do not use a low-input tier or assume a cache discount for the new policy.
The existing BudgetPolicy remains responsible for limits and other fields.
"""
    if not isinstance(snapshot, Mapping):
        raise ValueError('FINALE_REASONING_BUDGET_UNSUPPORTED')
    for key, minimum in (
        ('input_rate_cny', MIN_INPUT_RATE),
        ('cached_input_rate_cny', MIN_INPUT_RATE),
        ('output_rate_cny', MIN_OUTPUT_RATE),
    ):
        raw = snapshot.get(key)
        if not isinstance(raw, (str, int, float, Decimal)) or isinstance(raw, bool):
            raise ValueError('FINALE_REASONING_BUDGET_UNSUPPORTED')
        try:
            rate = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            raise ValueError('FINALE_REASONING_BUDGET_UNSUPPORTED') from None
        if not rate.is_finite() or rate < minimum:
            raise ValueError('FINALE_REASONING_BUDGET_UNSUPPORTED')


def _count(value):
    return type(value) is int and value >= 0


def normalize_reasoning_usage(raw):
    """Validate mandatory reasoning and inclusive text totals without mutation.

The unchanged generic normalizer enforces cache/total consistency after the
redundant inclusive completion text counter is removed from a shallow copy.
Unknown modality breakdowns are refused by this pure-text contract.
"""
    if not isinstance(raw, Mapping):
        return None
    completion = raw.get('completion_tokens')
    prompt = raw.get('prompt_tokens')
    details = raw.get('completion_tokens_details')
    if (not _count(completion) or not _count(prompt) or not isinstance(details, Mapping)
            or not set(details) <= {'text_tokens', 'reasoning_tokens'}):
        return None
    reasoning = details.get('reasoning_tokens')
    if not _count(reasoning) or reasoning > completion:
        return None
    if 'text_tokens' in details and (
            not _count(details['text_tokens']) or details['text_tokens'] != completion):
        return None
    prompt_details = raw.get('prompt_tokens_details')
    if prompt_details is not None:
        if (not isinstance(prompt_details, Mapping)
                or not set(prompt_details) <= {'text_tokens', 'cached_tokens'}):
            return None
        if 'text_tokens' in prompt_details and (
                not _count(prompt_details['text_tokens']) or prompt_details['text_tokens'] != prompt):
            return None
    adapted = dict(raw)
    adapted['completion_tokens_details'] = {'reasoning_tokens': reasoning}
    return normalize_provider_usage(adapted)


def reasoning_usage_error(raw, normalized, answer_limit):
    """Check answer admission separately from conservative usage accounting.

The caller may pass generic-normalizer accounting fallback. Always revalidate
raw reasoning semantics here, so missing counters cannot become zero reasoning.
"""
    reasoning_policy(answer_limit)
    trusted = normalize_reasoning_usage(raw)
    if trusted is None:
        return 'FINALE_REASONING_USAGE_INVALID'
    if not isinstance(normalized, UsageAmount) or any(
        getattr(normalized, key) != getattr(trusted, key)
        or not _count(getattr(normalized, key))
        for key in ('prompt_tokens', 'completion_tokens', 'cached_prompt_tokens', 'reasoning_tokens')
    ):
        return 'FINALE_REASONING_USAGE_MISMATCH'
    if trusted.reasoning_tokens > REASONING_TOKENS:
        return 'FINALE_REASONING_LIMIT_EXCEEDED'
    if trusted.completion_tokens - trusted.reasoning_tokens > answer_limit:
        return 'FINALE_REASONING_ANSWER_LIMIT_EXCEEDED'
    return None

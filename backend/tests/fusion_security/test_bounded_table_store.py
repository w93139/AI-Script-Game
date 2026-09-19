"""Durable opt-in reasoning accounting and five-seat recovery, without network."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json

import pytest
from sqlalchemy import update

from src.db.models.package_play import ScriptPackagePlay
from src.fusion.package_role_model import PackageRoleModel
from src.fusion.package_play import PackagePlayError, BOUNDED_TABLE_BINDING_CONTRACT
from src.fusion.package_table_model import BOUNDED_MODEL_CONTRACT, SCOPED_MODEL_CONTRACT
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_package_runtime import runtime
from tests.fusion_security.test_package_play_store import play, events, action_body
from tests.fusion_security.test_scoped_table_store import enter, service, assessment
from tests.fusion_security.test_full_play_decisions import decision
from tests.fusion_security.test_full_play_store import command
from tests.fusion_security.test_structured_finale import submission
from tests.fusion_security.test_reasoned_table_policy import stored_binding
from tests.fusion_security.test_bounded_table_policy import response


def configure(play):
    play.model = PackageRoleModel(play.sdk, replace(play.model.settings,
        provider='aliyun_bailian', model='qwen3.7-flash-2026-07-15'))
    play.policy = replace(play.policy, input_rate_cny=Decimal('0.6'),
                          cached_input_rate_cny=Decimal('0.6'), output_rate_cny=Decimal('2.4'))


def make_response(messages):
    wire = json.loads(messages[1].content)['context']
    r = response()
    r.content = canonical_json(assessment(wire))
    return r


@pytest.mark.parametrize('human', list('abcde'))
def test_five_roles_complete_with_private_reasoning_and_exact_persistent_accounting(play, human):
    configure(play)
    view = enter(play, human, BOUNDED_MODEL_CONTRACT); pid = view['play_id']
    binding = stored_binding(play)
    assert binding['schema_version'] == BOUNDED_TABLE_BINDING_CONTRACT
    assert binding['model']['thinking_mode'] == 'disabled'
    assert binding['seal_reasoning_policy']['reserved_output_tokens'] == 5136
    async def complete(messages, **params):
        assert not play.db.in_transaction()
        assert params['extra_body']['thinking_budget'] == 1024
        assert params['max_completion_tokens'] == 5120
        with play.factory() as db:
            assert service(play, db, policy=BOUNDED_MODEL_CONTRACT).get(pid, 1)['pending_ai']
        return make_response(messages)
    play.sdk.chat_completion.side_effect = complete
    view = play.play.table(pid, command(view['revision'], 'SEAL_FINALE', submission(human)), 1)
    for actor in 'abcde':
        if actor == human:
            continue
        req = decision(view['revision'], actor, 'SEAL_FINALE')
        view = asyncio.run(play.play.decide(pid, req, 1))
        assert view['last_ai_status'] == 'OK'
        assert asyncio.run(play.play.decide(pid, req, 1)) == view
    assert play.sdk.chat_completion.await_count == 4
    assert view['full_game']['finale']['all_sealed']
    view = play.play.act(pid, action_body(view['revision'], 'settle-final', 'SETTLE'), 1)
    assert view['settled']
    assert service(play, policy=BOUNDED_MODEL_CONTRACT, registry={}).get(pid, 1) == view
    records = [json.loads(e.event_json) for e in events(play)]
    requests = [e for e in records if e['kind'] == 'AI_REQUEST']
    results = [e for e in records if e['kind'] == 'AI_RESULT']
    assert len(requests) == len(results) == 4
    for e in requests:
        assert e['data']['reservation']['completion_tokens'] == 5136
        assert e['data']['model']['reasoning_policy'] == binding['seal_reasoning_policy']
    for e in results:
        used = e['data']['accounted']
        assert used['completion_tokens'] == 200 and used['reasoning_tokens'] == 50
        assert Decimal(used['cost_cny']) == Decimal('0.00054')
    assert 'PRIVATE_THOUGHT_SENTINEL' not in canonical_json(view)
    assert 'PRIVATE_THOUGHT_SENTINEL' not in canonical_json(records)
    assert stored_binding(play) == binding


@pytest.mark.parametrize('failure', ['transport', 'missing-usage', 'missing-reasoning', 'invalid-answer'])
def test_failures_keep_their_receipt_and_refresh_never_repeats_dispatch(play, failure):
    configure(play); view = enter(play, policy=BOUNDED_MODEL_CONTRACT); pid = view['play_id']
    async def complete(messages, **params):
        if failure == 'transport':
            raise RuntimeError('private transport error')
        r = make_response(messages)
        if failure == 'missing-usage': r.usage = None
        elif failure == 'missing-reasoning': r.usage['completion_tokens_details'].pop('reasoning_tokens')
        else: r.content = '{}'
        return r
    play.sdk.chat_completion.side_effect = complete
    req = decision(view['revision'], 'b', 'SEAL_FINALE')
    done = asyncio.run(play.play.decide(pid, req, 1))
    assert done['last_ai_status'] == ('UNKNOWN' if failure in ('transport', 'missing-usage') else 'INVALID')
    saved = [e.event_json for e in events(play)]
    assert service(play, policy=BOUNDED_MODEL_CONTRACT).get(pid, 1) == done
    assert asyncio.run(play.play.decide(pid, req, 1)) == done
    assert play.sdk.chat_completion.await_count == 1
    assert [e.event_json for e in events(play)] == saved
    request = next(json.loads(s) for s in saved if json.loads(s)['kind'] == 'AI_REQUEST')
    result = json.loads(saved[-1])
    if failure in ('transport', 'missing-usage'):
        assert result['data']['accounted'] == request['data']['reservation']
    else:
        assert result['data']['accounted']['completion_tokens'] == 200


def test_pending_cold_restart_keeps_frozen_request_and_accounting(play):
    configure(play); view = enter(play, policy=BOUNDED_MODEL_CONTRACT); pid = view['play_id']
    req = decision(view['revision'], 'b', 'SEAL_FINALE')
    _, prepared = play.play._begin(pid, req, 1)
    pending = play.play.get(pid, 1)
    current = service(play, policy=BOUNDED_MODEL_CONTRACT, registry={})
    assert current.get(pid, 1) == pending
    assert current._prepared_table_adapter(prepared).model_contract == BOUNDED_MODEL_CONTRACT
    assert asyncio.run(current.decide(pid, req, 1)) == pending
    assert play.sdk.chat_completion.await_count == 0


@pytest.mark.parametrize('field', ['reasoning_limit', 'reserved_output_tokens', 'provider_contract', 'new-field'])
def test_mutated_policy_is_rejected_even_with_recomputed_outer_hash(play, field):
    configure(play); view = enter(play, policy=BOUNDED_MODEL_CONTRACT)
    binding = stored_binding(play)
    binding['seal_reasoning_policy'][field] = 'changed'
    # Bypass the ORM's immutable-row guard to exercise read-time corruption
    # detection, as if persisted bytes had been damaged externally.
    play.db.execute(update(ScriptPackagePlay).values(
        binding_json=canonical_json(binding), binding_hash=content_hash(binding)))
    play.db.commit()
    with pytest.raises(PackagePlayError): play.play.get(view['play_id'], 1)
    assert play.sdk.chat_completion.await_count == 0


@pytest.mark.parametrize('invalid', ['provider', 'low-price'])
def test_unsupported_configuration_cannot_create_new_reasoning_binding(play, invalid):
    configure(play)
    if invalid == 'provider':
        play.model = PackageRoleModel(play.sdk, replace(play.model.settings,
            provider='ant_digital', model='qwen3.6-plus'))
    else:
        play.policy = replace(play.policy, input_rate_cny=Decimal('0.2'))
    with pytest.raises(PackagePlayError, match='FINALE_REASONING_'):
        enter(play, policy=BOUNDED_MODEL_CONTRACT)
    assert play.db.query(ScriptPackagePlay).count() == 0
    assert play.sdk.chat_completion.await_count == 0


def test_old_bound_game_keeps_its_disabled_adapter_after_new_policy_is_configured(play):
    configure(play); view = enter(play, policy=SCOPED_MODEL_CONTRACT)
    before = deepcopy(stored_binding(play)); rows = [e.event_json for e in events(play)]
    upgraded = service(play, policy=BOUNDED_MODEL_CONTRACT)
    assert upgraded.get(view['play_id'], 1) == view
    _, prepared = upgraded._begin(view['play_id'], decision(view['revision'], 'b', 'SEAL_FINALE'), 1)
    assert prepared['params']['extra_body']['enable_thinking'] is False
    assert 'reasoning_policy' not in prepared
    assert upgraded._prepared_table_adapter(prepared).model_contract == SCOPED_MODEL_CONTRACT
    assert stored_binding(play) == before
    assert [e.event_json for e in events(play)][:len(rows)] == rows


@pytest.mark.parametrize('corruption', ['reasoning-over', 'answer-over', 'prompt-over', 'zero-usage'])
def test_service_and_replay_reject_over_limit_ok_receipts_without_losing_cost(play, corruption):
    configure(play); view = enter(play, policy=BOUNDED_MODEL_CONTRACT); pid = view['play_id']
    req = decision(view['revision'], 'b', 'SEAL_FINALE')
    _, prepared = play.play._begin(pid, req, 1)
    async def complete(messages, **params): return make_response(messages)
    play.sdk.chat_completion.side_effect = complete
    result = asyncio.run(play.play._prepared_table_adapter(prepared).call(prepared))
    assert result['status'] == 'OK'
    row = play.play._row(pid, 1); package, binding = play.play._resolve(row)
    state = play.play._replay(row, package, binding)
    rid, pending = next(iter(state.pending.items()))
    usage = deepcopy(result['usage'])
    if corruption == 'reasoning-over': usage.update(completion_tokens=1200, reasoning_tokens=1025)
    elif corruption == 'answer-over': usage.update(completion_tokens=4100, reasoning_tokens=0)
    elif corruption == 'prompt-over': usage['prompt_tokens'] = prepared['input_tokens'] + 1
    else: usage.update(prompt_tokens=0, completion_tokens=0, reasoning_tokens=0)
    def replay_data(u):
        return {'status': 'OK', 'refs': [], 'usage': u,
            'accounted': play.play._account(play.policy, pending['reservation'], u).to_metadata(),
            'received_at': play.clock[0], 'decision': result['decision'], 'assessment': result['assessment']}
    command = {'idempotency_key': rid, 'request_id': rid}
    play.play._consume(deepcopy(state), 'AI_RESULT', command, replay_data(result['usage']), binding)
    with pytest.raises(ValueError, match='FINALE_REASONING_RECEIPT_INVALID'):
        play.play._consume(deepcopy(state), 'AI_RESULT', command, replay_data(usage), binding)
    done = play.play._finish(pid, rid, 1, {**result, 'usage': usage})
    assert done['last_ai_status'] == 'INVALID'
    assert service(play, policy=BOUNDED_MODEL_CONTRACT).get(pid, 1) == done
    recorded = json.loads(events(play)[-1].event_json)['data']
    assert recorded['usage'] == usage
    assert recorded['accounted'] == replay_data(usage)['accounted']
    assert play.sdk.chat_completion.await_count == 1

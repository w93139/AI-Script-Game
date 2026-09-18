"""MVP private finale brief: separate identity/body/event reasoning in table 1.2.

New 1.4 bindings freeze the policy; old event metadata or an explicit deployment
legacy policy preserve old games, including games with no table events. Keep
options, scoring, authorized context and one-attempt receipts unchanged. All
fixtures are fictional; no commercial text or expected hidden answer is added.
Verify via the guarded Fusion runner (table/decisions/finale/newbinding).
"""
import asyncio
from copy import deepcopy
import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import update

from src.db.models.package_play import ScriptPackagePlay
from src.fusion.package_play import PackagePlayService, PackagePlayError, TABLE_BINDING_CONTRACT
from src.fusion.package_table_model import (
    PackageTableModel, BoundPackageTableModel, ReasonedPackageTableModel,
    REASONED_MODEL_CONTRACT, BOUND_MODEL_CONTRACT, output_schema, table_context_window,
)
from src.fusion.package_validation import content_hash, canonical_json
from tests.fusion_security.test_package_runtime import runtime
from tests.fusion_security.test_package_play_store import play, start, events
from tests.fusion_security.test_package_full_play import full_package
from tests.fusion_security.test_bound_table_model import context, settings, answer, response
from tests.fusion_security import test_full_play_decisions as existing


def service(play, db=None, *, policy=REASONED_MODEL_CONTRACT, legacy='package-table-model/1.0', finale=None):
    return PackagePlayService(db if db is not None else play.db, play.publisher, play.model, play.policy,
        lambda: play.clock[0], table_policy=policy, legacy_table_policy=legacy, finale_policy=finale)


def stored_binding(play):
    return json.loads(play.db.query(ScriptPackagePlay).one().binding_json)


def test_reasoned_table_wire_preserves_every_material_question_and_private_uncertainty():
    c = context()
    c['materials'].append(dict(collection='evidence', id='one-action', text='机械计数器只记录一次动作。', kind='FACT', public=True))
    before = deepcopy(c)
    old = BoundPackageTableModel(object(), settings()); new = ReasonedPackageTableModel(object(), settings())
    prepared = new.prepare(c)
    assert json.loads(prepared['messages'][1]['content']) == json.loads(old.prepare(c)['messages'][1]['content'])
    assert prepared['params'] == old.prepare(c)['params']
    assert output_schema(c, REASONED_MODEL_CONTRACT) == output_schema(c, BOUND_MODEL_CONTRACT)
    prompt = prepared['messages'][0]['content']
    for rule in ['物理身体', '物件和具体时段事件', '不能虚构第二次动作', '未获回忆', '私密 answers', '单独写入 vote']:
        assert rule in prompt
    assert new.metadata()['prompt_hash'] != old.metadata()['prompt_hash']
    assert old.metadata()['prompt_hash'] == PackageTableModel(object(), settings()).metadata()['prompt_hash']
    value = answer(); value['answers'][0]['option_ids'] = []
    assert new._read_output(canonical_json(value), prepared)['decision'] == value
    assert c == before


def test_reasoned_table_window_accounts_for_new_prompt_without_trimming_required_sources():
    c = context(); c.pop('history_window')
    c['discussion'] = [dict(id=f'claim-{n}', sequence=n, speaker='a', kind='CLAIM', text='尚未核对的说法。' * 30) for n in range(1, 221)]
    model = ReasonedPackageTableModel(object(), settings())
    first = table_context_window(c, 65536, REASONED_MODEL_CONTRACT)
    limit = model.prepare(first)['input_tokens'] - 4097
    bounded = table_context_window(c, limit, REASONED_MODEL_CONTRACT)
    prepared = ReasonedPackageTableModel(object(), settings(max_input_bytes=limit)).prepare(bounded)
    assert prepared['input_tokens'] - 4096 <= limit
    assert bounded['materials'] == c['materials'] and bounded['questions'] == c['questions']
    assert len(bounded['discussion']) < len(first['discussion'])


@pytest.mark.parametrize('finale', [None, 'finale-motivation/1.3'])
def test_newbinding_freezes_table_and_nullable_finale_policies(play, finale):
    play.play = service(play, finale=finale)
    _, view = start(play, full_package())
    binding = stored_binding(play)
    assert binding['schema_version'] == TABLE_BINDING_CONTRACT
    assert binding['table_policy'] == REASONED_MODEL_CONTRACT
    assert binding['finale_motivation_policy'] == finale
    # Even a service whose current default is old must honor this new binding.
    assert service(play, policy='package-table-model/1.0').get(view['play_id'], 1) == view


@pytest.mark.parametrize('change', ['unknown-table', 'unknown-finale', 'missing-table', 'missing-finale', 'extra', 'legacy-fields'])
def test_newbinding_rejects_unknown_missing_or_cross_version_fields(play, change):
    play.play = service(play); _, view = start(play, full_package()); row = play.db.query(ScriptPackagePlay).one()
    binding = json.loads(row.binding_json)
    if change == 'unknown-table': binding['table_policy'] = 'package-table-model/99'
    elif change == 'unknown-finale': binding['finale_motivation_policy'] = 'finale-motivation/99'
    elif change == 'missing-table': del binding['table_policy']
    elif change == 'missing-finale': del binding['finale_motivation_policy']
    elif change == 'extra': binding['unapproved_policy'] = True
    else: binding['schema_version'] = 'package-text-play-binding/1.2'
    play.db.execute(update(ScriptPackagePlay).where(ScriptPackagePlay.id == row.id).values(binding_json=canonical_json(binding), binding_hash=content_hash(binding)))
    play.db.commit()
    with pytest.raises(PackagePlayError, match='SNAPSHOT_INVALID'): play.play.get(view['play_id'], 1)


@pytest.mark.parametrize('version', ['package-table-model/1.0', 'package-table-model/1.1'])
@pytest.mark.parametrize('prior_event', [False, True])
def test_old_table_games_remain_exact_with_and_without_previous_decisions(play, version, prior_event):
    play.play = service(play, policy=version, legacy=version)
    view = existing.open_ballot(play); pid = view['play_id']
    play.sdk.chat_completion.return_value = existing.output({'kind': 'ABSTAIN', 'choice_id': None})
    if prior_event: view = asyncio.run(play.play.decide(pid, existing.decision(view['revision']), 1))
    before_binding = deepcopy(stored_binding(play)); before_events = [e.event_json for e in events(play)]
    # Deliberately wrong legacy default with an event proves frozen metadata wins.
    upgraded = service(play, legacy=('package-table-model/1.0' if prior_event else version))
    assert upgraded.get(pid, 1) == view
    req = existing.decision(view['revision'], actor='c' if prior_event else 'b')
    result = asyncio.run(upgraded.decide(pid, req, 1))
    assert result['last_ai_status'] == 'OK'
    event = json.loads(events(play)[-2].event_json)
    assert event['data']['model']['schema_version'] == version
    assert stored_binding(play) == before_binding
    assert [e.event_json for e in events(play)][:len(before_events)] == before_events
    assert asyncio.run(upgraded.decide(pid, req, 1)) == result
    assert play.sdk.chat_completion.await_count == 1 + prior_event


@pytest.mark.parametrize('version', ['package-table-model/1.0', 'package-table-model/1.1', REASONED_MODEL_CONTRACT])
def test_table_pending_after_default_change_never_reenters_sdk(play, version):
    play.play = service(play, policy=version, legacy='package-table-model/1.1' if version.endswith('1.1') else 'package-table-model/1.0')
    view = existing.open_ballot(play); req = existing.decision(view['revision']); pid = view['play_id']
    _, prepared = play.play._begin(pid, req, 1)
    assert prepared and play.sdk.chat_completion.await_count == 0
    upgraded = service(play, legacy='package-table-model/1.1')
    pending = upgraded.get(pid, 1)
    assert pending['pending_ai']
    assert asyncio.run(upgraded.decide(pid, req, 1)) == pending
    play.clock[0] += 100
    expired = asyncio.run(upgraded.decide(pid, req, 1))
    assert expired['last_ai_status'] == 'EXPIRED'
    assert play.sdk.chat_completion.await_count == 0


def test_reasoned_table_complete_five_seat_settlement_and_reload_without_finale_speeches(play):
    play.play = service(play)
    with patch.object(existing, 'service', service):
        existing.test_full_play_complete_persistent_five_seat_model_submissions_and_settlement(play)
    binding = stored_binding(play)
    assert binding['finale_motivation_policy'] is None
    for event in events(play):
        body = json.loads(event.event_json)
        if body['kind'] == 'AI_REQUEST': assert body['data']['model']['schema_version'] == REASONED_MODEL_CONTRACT


@pytest.mark.parametrize('bad', [True, 'package-table-model/1.2', 'package-table-model/99'])
def test_legacy_table_fallback_cannot_upgrade_unbound_old_games(play, bad):
    with pytest.raises(PackagePlayError, match='LEGACY_TABLE_POLICY_INVALID'): service(play, legacy=bad)


def test_bound_table_existing_wire_snapshot_remains_stable():
    old = BoundPackageTableModel(object(), settings())
    assert content_hash(old.metadata()) == '43dc09b53b7fc59e638ba0c396851769bf1f07eabcde0b156d256f08a94e2513'
    assert content_hash(old.prepare(context())) == '314f1a84604801aa654deb215bb46cd9dcfe4a6bcca20fa3d0dc89bf1f682834'
    assert content_hash(output_schema(context(), BOUND_MODEL_CONTRACT)) == 'db6fc98d7e5e13cc33a66e1ca28b4ddab1fc466ace297f3c589c0b8a0dfb84dd'


def test_newbinding_dispatch_keeps_reasoned_policy_when_server_default_returns_to_legacy(play):
    play.play = service(play); view = existing.open_ballot(play); pid = view['play_id']
    legacy_default = service(play, policy='package-table-model/1.0')
    play.sdk.chat_completion.return_value = existing.output({'kind': 'ABSTAIN', 'choice_id': None})
    result = asyncio.run(legacy_default.decide(pid, existing.decision(view['revision']), 1))
    assert result['last_ai_status'] == 'OK'
    assert json.loads(events(play)[-2].event_json)['data']['model']['schema_version'] == REASONED_MODEL_CONTRACT
    assert '不能虚构第二次动作' in play.sdk.chat_completion.call_args.args[0][0].content


@pytest.mark.parametrize('bound', [False, True])
def test_table_replay_rejects_cross_binding_model_substitution(play, bound):
    play.play = service(play, policy=REASONED_MODEL_CONTRACT if bound else BOUND_MODEL_CONTRACT, legacy=BOUND_MODEL_CONTRACT)
    view = existing.open_ballot(play); pid = view['play_id']
    row = play.play._row(pid, 1); package, binding = play.play._resolve(row)
    prior_state = play.play._replay(row, package, binding)
    request = existing.decision(view['revision'])
    play.play._begin(pid, request, 1)
    data = json.loads(events(play)[-1].event_json)['data']
    other = BOUND_MODEL_CONTRACT if bound else REASONED_MODEL_CONTRACT
    data['model'] = play.play._table_model_for_policy(other).metadata()
    # Tiny fixture retains its exact context across these policies. The frozen
    # binding itself must still prevent introducing/replacing the new policy.
    assert data['context_hash'] == content_hash(play.play._table_context(prior_state, binding, 'b', 'CAST_BALLOT', version=other))
    with pytest.raises(ValueError): play.play._consume(prior_state, 'AI_REQUEST', request, data, binding)
    assert play.sdk.chat_completion.await_count == 0


def test_reasoned_table_tampering_rejects_before_sdk_and_original_decision_is_not_repaired():
    sdk = AsyncMock(); model = ReasonedPackageTableModel(sdk, settings())
    prepared = model.prepare(context()); bad = deepcopy(prepared)
    bad['messages'][0]['content'] = BoundPackageTableModel(object(), settings()).prepare(context())['messages'][0]['content']
    assert asyncio.run(model.call(bad))['model_attempted'] is False
    sdk.chat_completion.assert_not_awaited()
    wrong = answer(); wrong['answers'][0]['option_ids'] = ['north']
    sdk.chat_completion.return_value = response(wrong)
    result = asyncio.run(model.call(prepared))
    assert result['status'] == 'INVALID' and 'decision' not in result
    assert wrong['answers'][0]['option_ids'] == ['north']
    assert sdk.chat_completion.await_count == 1


def test_reasoned_table_ant_wire_size_covers_actual_schema_restatement():
    cfg = settings(provider='ant_digital', model='qwen3.6-plus')
    model = ReasonedPackageTableModel(object(), cfg)
    c = context(); c.pop('history_window')
    window = table_context_window(c, 65536, REASONED_MODEL_CONTRACT, provider_model=model.metadata())
    prepared = model.prepare(window)
    assert prepared['input_tokens'] - 4096 == len(canonical_json(prepared['messages']).encode()) + len(canonical_json(prepared['params']['response_format']).encode())
    assert json.loads(prepared['messages'][1]['content'])['context']['materials'] == c['materials']

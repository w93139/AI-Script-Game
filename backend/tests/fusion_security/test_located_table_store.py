"""Offline persistence and permission boundary for newly bound table 1.4."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import update

from src.db.models.package_play import ScriptPackagePlay
from src.fusion.package_play import PackagePlayService, PackagePlayError, LOCATED_TABLE_BINDING_CONTRACT
from src.fusion.package_table_model import LOCATED_MODEL_CONTRACT, EVIDENCE_MODEL_CONTRACT
from src.fusion.located_evidence import authorized_evidence_origins
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_package_runtime import runtime
from tests.fusion_security.test_package_play_store import play, events, action_body
from tests.fusion_security.test_full_play_decisions import decision, output
from tests.fusion_security.test_structured_finale import submission
from tests.fusion_security.test_full_play_store import command
from tests.fusion_security import test_finale_motivation as finale
from tests.fusion_security.test_reasoned_table_policy import stored_binding
from tests.fusion_security.test_evidence_table_store import unknown as old_unknown


def service(play, db=None, *, enabled=False, policy=LOCATED_MODEL_CONTRACT, legacy='package-table-model/1.0'):
    return PackagePlayService(play.db if db is None else db, play.publisher, play.model, play.policy,
        lambda: play.clock[0], guided_content=getattr(play, 'finale_guides', {}),
        table_policy=policy, legacy_table_policy=legacy)


def enter(play, policy=LOCATED_MODEL_CONTRACT):
    legacy = policy if policy in ('package-table-model/1.0', 'package-table-model/1.1') else 'package-table-model/1.0'
    with patch.object(finale, 'service', lambda p, **kw: service(p, policy=policy, legacy=legacy)):
        return finale.enter_finale(play, enabled=False)[2]


def assessment(wire):
    result = old_unknown(wire)
    result['schema_version'] = 'table-evidence-assessment/1.1'
    # These fictional selections exercise storage, not a source-entailment oracle.
    for item, question in zip(result['answers'], wire['questions'], strict=True):
        if question['options']:
            item['selections'] = [{'option_id': question['options'][0]['id'], 'certainty': 'INFERRED',
                'basis': ['e:evidence-look-note/p1'], 'summary': '合成私卷存储验证，保留有限推测。'}]
    return result


def test_new_binding_four_seals_settlement_refresh_and_private_assessments(play):
    view = enter(play); pid = view['play_id']; binding = stored_binding(play)
    assert binding['schema_version'] == LOCATED_TABLE_BINDING_CONTRACT
    assert binding['table_policy'] == LOCATED_MODEL_CONTRACT
    assert binding['finale_motivation_policy'] is None
    assert binding['full_output']['max_output_tokens'] == 4096
    observed = []
    async def complete(messages, **params):
        wire = json.loads(messages[1].content)['context']; observed.append(wire)
        assert wire['schema_version'] == 'package-table-context/1.3'
        assert wire['evidence_origins'] == [
            {'id': 'evidence-find-key', 'labels': ['find-key']},
            {'id': 'evidence-open-box', 'labels': ['open-box']},
            {'id': 'evidence-look-note', 'labels': ['look-note']}]
        assert all('text' not in m and 'passages' in m for m in wire['materials'])
        assert 'SYSTEM_TRUTH' not in canonical_json(wire) and 'PRIVATE_BOOK_a' not in canonical_json(wire)
        assert params['max_tokens'] == 4096
        return output(assessment(wire))
    play.sdk.chat_completion.side_effect = complete
    view = play.play.table(pid, command(view['revision'], 'SEAL_FINALE', submission('a')), 1)
    for actor in 'bcde':
        req = decision(view['revision'], actor, 'SEAL_FINALE')
        view = asyncio.run(play.play.decide(pid, req, 1))
        assert view['last_ai_status'] == 'OK'
        assert asyncio.run(play.play.decide(pid, req, 1)) == view
        with play.factory() as db: assert service(play, db).get(pid, 1) == view
        assert 'assessment' not in canonical_json(view) and 'e:evidence-look-note/p1' not in canonical_json(view)
    view = play.play.act(pid, action_body(view['revision'], 'settle-located', 'SETTLE'), 1)
    assert view['settled'] and len(observed) == play.sdk.chat_completion.await_count == 4
    assert service(play, policy='package-table-model/1.0').get(pid, 1) == view
    data = [json.loads(e.event_json)['data'] for e in events(play) if e.kind == 'AI_RESULT']
    assert len(data) == 4 and all(d['assessment']['schema_version'] == 'table-evidence-assessment/1.1' for d in data)
    assert all(d['decision']['answers'][0]['option_ids'] for d in data)
    assert all('assessment' not in d['decision'] for d in data)
    assert 'assessment' not in canonical_json(view)


@pytest.mark.parametrize('change', ['missing', 'old_assessment', 'foreign_reference', 'other_collection', 'projection', 'vote'])
def test_located_result_replay_rejects_assessment_or_projection_tampering(play, change):
    view = enter(play); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    row = play.play._row(pid, 1); package, binding = play.play._resolve(row)
    _, prepared = play.play._begin(pid, req, 1); prior = play.play._replay(row, package, binding)
    wire = json.loads(prepared['messages'][1]['content'])['context']
    play.sdk.chat_completion.return_value = output(assessment(wire))
    result = asyncio.run(play.play._prepared_table_adapter(prepared).call(prepared))
    done = play.play._finish(pid, req['idempotency_key'], 1, result)
    assert done['last_ai_status'] == 'OK'
    event = events(play)[-1]; data = deepcopy(json.loads(event.event_json)['data'])
    if change == 'missing': del data['assessment']
    elif change == 'old_assessment': data['assessment']['schema_version'] = 'table-evidence-assessment/1.0'
    elif change == 'foreign_reference': data['assessment']['answers'][0]['selections'][0]['basis'] = ['e:unacquired/p1']
    elif change == 'other_collection': data['assessment']['answers'][0]['selections'][0]['basis'] = ['k:evidence-look-note/p1']
    elif change == 'projection': data['decision']['answers'][0]['option_ids'] = []
    else: data['assessment']['vote']['trust_character_id'] = 'c'
    with pytest.raises(ValueError):
        play.play._consume(deepcopy(prior), 'AI_RESULT', json.loads(event.request_json), data, binding)
    assert service(play).get(pid, 1) == done


def test_new_request_replay_rejects_different_authorized_location_context_hash(play):
    view = enter(play); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    row = play.play._row(pid, 1); package, binding = play.play._resolve(row)
    prior = play.play._replay(row, package, binding)
    _, prepared = play.play._begin(pid, req, 1)
    data = deepcopy(json.loads(events(play)[-1].event_json)['data'])
    altered = deepcopy(prepared['source_context']); altered['evidence_origins'][0]['labels'] = ['未完成的地点']
    data['context_hash'] = content_hash(altered)
    with pytest.raises(ValueError): play.play._consume(prior, 'AI_REQUEST', req, data, binding)
    assert play.sdk.chat_completion.await_count == 0


@pytest.mark.parametrize('failure', ['invalid', 'unknown', 'expired'])
def test_located_failure_receipt_replays_once_then_explicit_new_request_recovers(play, failure):
    view = enter(play); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    if failure == 'expired': play.play._begin(pid, req, 1); play.clock[0] += 301
    elif failure == 'unknown': play.sdk.chat_completion.side_effect = RuntimeError('transport')
    else: play.sdk.chat_completion.return_value = output(submission('b'))
    done = asyncio.run(play.play.decide(pid, req, 1))
    assert done['last_ai_status'] == failure.upper()
    failure_record = events(play)[-1].event_json; data = json.loads(failure_record)['data']
    assert data['decision'] is None and data['assessment'] is None
    assert service(play).get(pid, 1) == done
    assert asyncio.run(play.play.decide(pid, req, 1)) == done
    first_calls = 0 if failure == 'expired' else 1
    assert play.sdk.chat_completion.await_count == first_calls
    async def recover(messages, **params): return output(assessment(json.loads(messages[1].content)['context']))
    play.sdk.chat_completion.side_effect = recover
    recovered = asyncio.run(service(play).decide(pid, decision(done['revision'], 'b', 'SEAL_FINALE'), 1))
    assert recovered['last_ai_status'] == 'OK'
    assert play.sdk.chat_completion.await_count == first_calls + 1
    assert failure_record in [e.event_json for e in events(play)]
    assert service(play).get(pid, 1) == recovered


@pytest.mark.parametrize('policy', ['package-table-model/1.0', 'package-table-model/1.1', 'package-table-model/1.2', EVIDENCE_MODEL_CONTRACT])
@pytest.mark.parametrize('prior_seal', [False, True])
def test_new_service_keeps_old_policy_context_and_results_with_or_without_table_events(play, policy, prior_seal):
    view = enter(play, policy); pid = view['play_id']; binding = stored_binding(play)
    async def complete(messages, **params):
        wire = json.loads(messages[1].content)['context']
        assert 'evidence_origins' not in wire
        return output(old_unknown(wire) if policy == EVIDENCE_MODEL_CONTRACT else submission(wire['character']['id']))
    play.sdk.chat_completion.side_effect = complete
    if prior_seal: view = asyncio.run(play.play.decide(pid, decision(view['revision'], 'b', 'SEAL_FINALE'), 1))
    before = [e.event_json for e in events(play)]
    newer = service(play, legacy=policy if policy.endswith(('1.0', '1.1')) else 'package-table-model/1.0')
    actor = 'c' if prior_seal else 'b'
    result = asyncio.run(newer.decide(pid, decision(view['revision'], actor, 'SEAL_FINALE'), 1))
    assert result['last_ai_status'] == 'OK' and newer.get(pid, 1) == result
    assert json.loads(events(play)[-2].event_json)['data']['model']['schema_version'] == policy
    data = json.loads(events(play)[-1].event_json)['data']
    assert ('assessment' in data) == (policy == EVIDENCE_MODEL_CONTRACT)
    if 'assessment' in data: assert data['assessment']['schema_version'] == 'table-evidence-assessment/1.0'
    assert stored_binding(play) == binding
    assert [e.event_json for e in events(play)][:len(before)] == before


@pytest.mark.parametrize('policy', ['package-table-model/1.0', 'package-table-model/1.1', 'package-table-model/1.2', EVIDENCE_MODEL_CONTRACT, LOCATED_MODEL_CONTRACT])
def test_pending_seal_under_new_default_is_never_redispatched(play, policy):
    view = enter(play, policy); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    play.play._begin(pid, req, 1); before = [e.event_json for e in events(play)]
    newer = service(play, legacy=policy if policy.endswith(('1.0', '1.1')) else 'package-table-model/1.0')
    pending = newer.get(pid, 1)
    assert asyncio.run(newer.decide(pid, req, 1)) == pending
    assert [e.event_json for e in events(play)] == before
    play.clock[0] += 301
    expired = asyncio.run(newer.decide(pid, req, 1))
    assert expired['last_ai_status'] == 'EXPIRED' and asyncio.run(newer.decide(pid, req, 1)) == expired
    assert play.sdk.chat_completion.await_count == 0
    data = json.loads(events(play)[-1].event_json)['data']
    assert ('assessment' in data) == (policy in (EVIDENCE_MODEL_CONTRACT, LOCATED_MODEL_CONTRACT))


@pytest.mark.parametrize('change', ['old_policy', 'missing_policy', 'missing_finale', 'unknown_finale', 'old_binding_schema', 'extra'])
def test_binding_16_rejects_missing_cross_version_and_unknown_policy_fields(play, change):
    view = enter(play); binding = stored_binding(play); row = play.db.query(ScriptPackagePlay).one()
    if change == 'old_policy': binding['table_policy'] = EVIDENCE_MODEL_CONTRACT
    elif change == 'missing_policy': del binding['table_policy']
    elif change == 'missing_finale': del binding['finale_motivation_policy']
    elif change == 'unknown_finale': binding['finale_motivation_policy'] = 'finale-motivation/99'
    elif change == 'old_binding_schema': binding['schema_version'] = 'package-text-play-binding/1.5'
    else: binding['hidden_answer_mode'] = True
    play.db.execute(update(ScriptPackagePlay).where(ScriptPackagePlay.id == row.id).values(
        binding_json=canonical_json(binding), binding_hash=content_hash(binding)))
    play.db.commit()
    with pytest.raises(PackagePlayError, match='SNAPSHOT_INVALID'): service(play).get(view['play_id'], 1)


def test_origins_only_use_visible_evidence_and_completed_direct_release_labels():
    package = {'evidence': [
        {'id': 'visible', 'release': {'required_action_ids': ['open-card', 'same-label', 'not-done']}},
        {'id': 'private-unacquired', 'release': {'required_action_ids': ['find-key']}},
        {'id': 'not-physical', 'release': {'required_action_ids': ['find-key']}}],
        'mechanics': {'actions': [
            {'id': 'find-key', 'label': '前置钥匙房', 'required_action_ids': []},
            {'id': 'open-card', 'label': '直接调查', 'required_action_ids': ['find-key']},
            {'id': 'same-label', 'label': '直接调查', 'required_action_ids': []},
            {'id': 'not-done', 'label': '未完成房间', 'required_action_ids': []}]}}
    engine = SimpleNamespace(_package=package, state=lambda: {'completed_action_ids': ['find-key', 'open-card', 'same-label']})
    materials = [{'collection': 'evidence', 'id': 'visible'}, {'collection': 'knowledge', 'id': 'not-physical'}]
    before = deepcopy(package)
    assert authorized_evidence_origins(engine, materials) == [{'id': 'visible', 'labels': ['直接调查']}]
    assert authorized_evidence_origins(engine, []) == []
    assert package == before

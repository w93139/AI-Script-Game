"""New sealed evidence survives replay privately; old bindings stay frozen."""
import asyncio
from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from src.fusion.package_play import PackagePlayService, PackagePlayError, EVIDENCE_TABLE_BINDING_CONTRACT
from src.fusion.package_table_model import EVIDENCE_MODEL_CONTRACT
from src.fusion.package_validation import canonical_json
from tests.fusion_security.test_package_runtime import runtime
from tests.fusion_security.test_package_play_store import play, events, action_body
from tests.fusion_security.test_full_play_decisions import decision, output
from tests.fusion_security.test_structured_finale import submission
from tests.fusion_security.test_full_play_store import command
from tests.fusion_security import test_finale_motivation as finale
from tests.fusion_security import test_reasoned_table_policy as old


def service(play, db=None, *, enabled=True, policy=EVIDENCE_MODEL_CONTRACT, legacy='package-table-model/1.0'):
    return PackagePlayService(play.db if db is None else db, play.publisher, play.model, play.policy,
        lambda: play.clock[0], guided_content=getattr(play, 'finale_guides', {}),
        table_policy=policy, legacy_table_policy=legacy)


def enter(play):
    with patch.object(finale, 'service', service):
        return finale.enter_finale(play, enabled=False)[2]


def unknown(wire):
    return {'schema_version': 'table-evidence-assessment/1.0',
            'answers': [{'question_id': q['id'], 'selections': []} for q in wire['questions']],
            'vote': {'accusation_id': None, 'trust_character_id': None},
            'reflection': {'text': '', 'certainty': 'UNKNOWN', 'basis': []}}


def test_evidence_binding_four_private_assessments_full_settlement_refresh_and_idempotency(play):
    view = enter(play); pid = view['play_id']
    row = play.play._row(pid, 1); package, binding = play.play._resolve(row)
    assert binding['schema_version'] == EVIDENCE_TABLE_BINDING_CONTRACT
    assert binding['table_policy'] == EVIDENCE_MODEL_CONTRACT and binding['finale_motivation_policy'] is None
    async def sdk(messages, **params):
        wire = json.loads(messages[1].content)['context']
        assert wire['schema_version'] == 'package-table-context/1.1'
        assert all('passages' in m and 'text' not in m for m in wire['materials'])
        assert 'SYSTEM_TRUTH' not in canonical_json(wire)
        return output(unknown(wire))
    play.sdk.chat_completion.side_effect = sdk
    view = play.play.table(pid, command(view['revision'], 'SEAL_FINALE', submission('a')), 1)
    for actor in 'bcde':
        req = decision(view['revision'], actor, 'SEAL_FINALE')
        view = asyncio.run(play.play.decide(pid, req, 1))
        assert view['last_ai_status'] == 'OK'
        assert asyncio.run(play.play.decide(pid, req, 1)) == view
        assert service(play).get(pid, 1) == view
        assert 'assessment' not in canonical_json(view) and 'passage_id' not in canonical_json(view)
    view = play.play.act(pid, action_body(view['revision'], 'settle-evidence', 'SETTLE'), 1)
    assert view['settled'] and play.sdk.chat_completion.await_count == 4
    assert service(play, policy='package-table-model/1.0').get(pid, 1) == view
    assert 'assessment' not in canonical_json(view)
    data = [json.loads(e.event_json)['data'] for e in events(play) if json.loads(e.event_json)['kind'] == 'AI_RESULT']
    assert len(data) == 4 and all(d['assessment']['answers'] for d in data)
    assert all(not a['option_ids'] for d in data for a in d['decision']['answers'])


@pytest.mark.parametrize('change', ['missing', 'altered', 'projection', 'foreign'])
def test_evidence_result_replay_rejects_proof_omission_or_substitution(play, change):
    view = enter(play); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    row = play.play._row(pid, 1); package, binding = play.play._resolve(row)
    _, prepared = play.play._begin(pid, req, 1)
    prior = play.play._replay(row, package, binding)
    wire = json.loads(prepared['messages'][1]['content'])['context']
    play.sdk.chat_completion.return_value = output(unknown(wire))
    result = asyncio.run(play.play._prepared_table_adapter(prepared).call(prepared))
    done = play.play._finish(pid, req['idempotency_key'], 1, result)
    assert done['last_ai_status'] == 'OK'
    body = json.loads(events(play)[-1].event_json); data = deepcopy(body['data'])
    if change == 'missing': del data['assessment']
    elif change == 'altered': data['assessment']['vote']['trust_character_id'] = 'c'
    elif change == 'projection': data['decision']['reflection'] = '不在原回执中的反思'
    else:
        q = wire['questions'][0]
        data['assessment']['answers'][0]['selections'] = [{'option_id': q['options'][0]['id'], 'certainty': 'DIRECT', 'basis': ['m9999.p0001'], 'summary': '伪造引用'}]
    with pytest.raises(ValueError): play.play._consume(deepcopy(prior), 'AI_RESULT', json.loads(events(play)[-1].request_json), data, binding)
    assert service(play).get(pid, 1) == done


@pytest.mark.parametrize('failure', ['invalid', 'unknown', 'expired'])
def test_failed_evidence_receipts_keep_null_proof_and_do_not_retry(play, failure):
    view = enter(play); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    if failure == 'expired':
        play.play._begin(pid, req, 1); play.clock[0] += 301
    elif failure == 'unknown': play.sdk.chat_completion.side_effect = RuntimeError('transport')
    else: play.sdk.chat_completion.return_value = output(submission('b'))
    done = asyncio.run(play.play.decide(pid, req, 1))
    assert done['last_ai_status'] == failure.upper()
    data = json.loads(events(play)[-1].event_json)['data']
    assert data['decision'] is None and data['assessment'] is None
    assert service(play).get(pid, 1) == done
    assert asyncio.run(play.play.decide(pid, req, 1)) == done
    assert play.sdk.chat_completion.await_count == (0 if failure == 'expired' else 1)


@pytest.mark.parametrize('policy', ['package-table-model/1.0', 'package-table-model/1.1', 'package-table-model/1.2'])
def test_old_sealed_request_after_default_upgrade_keeps_old_shape_and_metadata(play, policy):
    with patch.object(finale, 'service', lambda p, **kw: service(p, policy=policy)):
        view = finale.enter_finale(play, enabled=False)[2]
    pid = view['play_id']; frozen_binding = old.stored_binding(play)
    prior = [e.event_json for e in events(play)]
    newer = service(play, legacy=policy if not policy.endswith('1.2') else 'package-table-model/1.0')
    play.sdk.chat_completion.return_value = output(submission('b'))
    result = asyncio.run(newer.decide(pid, decision(view['revision'], 'b', 'SEAL_FINALE'), 1))
    assert result['last_ai_status'] == 'OK'
    data = json.loads(events(play)[-1].event_json)['data']
    assert 'assessment' not in data
    assert json.loads(events(play)[-2].event_json)['data']['model']['schema_version'] == policy
    assert old.stored_binding(play) == frozen_binding
    assert [e.event_json for e in events(play)][:len(prior)] == prior
    assert newer.get(pid, 1) == result


@pytest.mark.parametrize('policy', ['package-table-model/1.2', EVIDENCE_MODEL_CONTRACT])
def test_pending_seal_default_change_expires_once_without_dispatch(play, policy):
    with patch.object(finale, 'service', lambda p, **kw: service(p, policy=policy)):
        view = finale.enter_finale(play, enabled=False)[2]
    pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    play.play._begin(pid, req, 1)
    saved = [e.event_json for e in events(play)]
    newer = service(play)
    waiting = newer.get(pid, 1)
    assert asyncio.run(newer.decide(pid, req, 1)) == waiting
    assert [e.event_json for e in events(play)] == saved
    play.clock[0] += 301
    expired = asyncio.run(newer.decide(pid, req, 1))
    assert expired['last_ai_status'] == 'EXPIRED'
    data = json.loads(events(play)[-1].event_json)['data']
    assert ('assessment' in data) == (policy == EVIDENCE_MODEL_CONTRACT)
    assert asyncio.run(newer.decide(pid, req, 1)) == expired
    assert play.sdk.chat_completion.await_count == 0


def test_new_table_binding_respects_disabled_current_model(play):
    view = enter(play); newer = service(play)
    newer.table_model.available = False
    with pytest.raises(PackagePlayError, match='AI_UNAVAILABLE'):
        asyncio.run(newer.decide(view['play_id'], decision(view['revision'], 'b', 'SEAL_FINALE'), 1))
    assert play.sdk.chat_completion.await_count == 0
    assert not newer.get(view['play_id'], 1)['pending_ai']

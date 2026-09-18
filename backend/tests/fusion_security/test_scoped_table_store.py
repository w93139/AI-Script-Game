"""New scoped finale binding: shared human/AI wording and old-game isolation."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from unittest.mock import patch

import pytest
from sqlalchemy import update

from src.db.models.package_play import ScriptPackagePlay
from src.fusion.finale_question_scopes import FinaleQuestionScopes
from src.fusion.package_play import PackagePlayService, PackagePlayError, SCOPED_TABLE_BINDING_CONTRACT
from src.fusion.package_table_model import SCOPED_MODEL_CONTRACT, LOCATED_MODEL_CONTRACT, EVIDENCE_MODEL_CONTRACT
from src.fusion.package_validation import canonical_json, content_hash, validate_package
from tests.fusion_security.test_package_runtime import runtime
from tests.fusion_security.test_package_play_store import play, events, action_body
from tests.fusion_security.test_package_full_play import full_package
from tests.fusion_security.test_structured_finale import submission
from tests.fusion_security.test_full_play_store import command
from tests.fusion_security.test_full_play_decisions import decision, output
from tests.fusion_security.test_evidence_table_store import unknown as old_unknown
from tests.fusion_security.test_located_table_store import assessment as located_assessment
from tests.fusion_security.test_reasoned_table_policy import stored_binding
from tests.fusion_security import test_finale_motivation as finale


def digest(value):
    return sha256(value.encode()).hexdigest()


def catalogues(package):
    docs = {}
    for actor in 'abcde':
        q = next(q for q in package['full_play']['finale']['questions'] if q['character_id'] == actor)
        material_id = ('gated-' if any(m['id'] == 'gated-' + actor for m in package['knowledge']) else 'initial-') + actor
        material = next(m for m in package['knowledge'] if m['id'] == material_id)
        doc = {'schema_version': 'finale-question-scopes/1.0', 'package_hash': content_hash(package),
            'character_id': actor, 'questions': [{'question_id': q['id'],
                'original_prompt_sha256': digest(q['prompt']), 'prompt': f'SCOPE_{actor}：只讨论此前那次旅行，未知留空。',
                'basis': [{'collection': 'knowledge', 'id': material['id'], 'text_sha256': digest(material['text'])}]}]}
        docs[actor] = FinaleQuestionScopes(package, doc)
    return {content_hash(package): docs}


def service(play, db=None, *, policy=SCOPED_MODEL_CONTRACT, registry=None, legacy='package-table-model/1.0'):
    return PackagePlayService(play.db if db is None else db, play.publisher, play.model, play.policy,
        lambda: play.clock[0], guided_content=getattr(play, 'finale_guides', {}),
        table_policy=policy, legacy_table_policy=legacy,
        finale_question_scopes=getattr(play, 'scope_catalogues', {}) if registry is None else registry)


def enter(play, human='a', policy=SCOPED_MODEL_CONTRACT, gated=False):
    package = full_package()
    if gated:
        hidden = deepcopy(package['evidence'][0])
        hidden.update(id='never-shared', visibility='CHARACTER_PRIVATE', character_id='e',
                      disclosure='MAY_SHARE', release={'phase_id': 'read-one', 'required_action_ids': []})
        package['evidence'].append(hidden)
        for original in package['knowledge'][:2]:
            material = deepcopy(original)
            material.update(id='gated-' + original['character_id'], text='HIDDEN_SCOPE_' + original['character_id'])
            material['release']['required_public_evidence_ids'] = ['never-shared']
            package['knowledge'].append(material)
    assert validate_package(package)['valid'], validate_package(package)
    play.scope_catalogues = catalogues(package)
    legacy = policy if policy in ('package-table-model/1.0', 'package-table-model/1.1') else 'package-table-model/1.0'
    with patch.object(finale, 'full_package', lambda: deepcopy(package)), \
            patch.object(finale, 'service', lambda p, **kw: service(p, policy=policy, legacy=legacy)):
        return finale.enter_finale(play, human, enabled=False)[2]


def assessment(wire):
    value = old_unknown(wire); value['schema_version'] = 'table-evidence-assessment/1.2'
    q = wire['questions'][0]; option = q['options'][0]
    value['answers'][0]['selections'] = [{'option_id': option['id'], 'option_text': option['label'],
        'certainty': 'INFERRED', 'basis': ['e:evidence-look-note/p1'], 'summary': '合成资料支持的有限候选。'}]
    return value


@pytest.mark.parametrize('human', list('abcde'))
def test_new_binding_scopes_human_and_ai_same_sources_without_cross_role_leak(play, human):
    view = enter(play, human); pid = view['play_id']; binding = stored_binding(play)
    assert binding['schema_version'] == SCOPED_TABLE_BINDING_CONTRACT
    assert binding['table_policy'] == SCOPED_MODEL_CONTRACT
    assert set(binding['finale_question_scopes']) == set('abcde')
    form = view['full_game']['finale']['questions']
    assert form[0]['prompt'].startswith('SCOPE_' + human)
    assert all('SCOPE_' + actor not in canonical_json(view) for actor in 'abcde' if actor != human)
    assert 'original_prompt_sha256' not in canonical_json(view) and 'question_scopes' not in canonical_json(view)
    assert play.sdk.chat_completion.await_count == 0
    row = play.play._row(pid, 1); package, binding = play.play._resolve(row)
    original = deepcopy(play.play._replay(row, package, binding).engine.state())
    actor = next(a for a in 'abcde' if a != human)
    request = decision(view['revision'], actor, 'SEAL_FINALE')
    _, prepared = play.play._begin(pid, request, 1)
    raw = prepared['source_context']; wire = json.loads(prepared['messages'][1]['content'])['context']
    assert raw['schema_version'] == 'package-table-context/1.4'
    assert raw['questions'][0]['prompt'] == actor + '-private-prompt'
    assert len(raw['question_scopes']) == 1
    assert wire['questions'][0]['prompt'] == binding['finale_question_scopes'][actor]['questions'][0]['prompt']
    assert wire['questions'][0]['options'] == raw['questions'][0]['options']
    assert wire['questions'][0]['max_choices'] == raw['questions'][0]['max_choices']
    assert 'SCOPE_' + human not in canonical_json(wire)
    assert 'SYSTEM_TRUTH' not in canonical_json(wire) and 'PRIVATE_BOOK_' + human not in canonical_json(wire)
    assert play.play._replay(row, package, binding).engine.state() == original
    assert service(play, registry={}).get(pid, 1)['full_game']['finale']['questions'] == form


def test_frozen_scope_snapshot_survives_registry_changes_refresh_and_new_service(play):
    view = enter(play); pid = view['play_id']; before = deepcopy(stored_binding(play))
    row = play.play._row(pid, 1); package, _ = play.play._resolve(row)
    replacement = catalogues(package)
    for actor, old in replacement[content_hash(package)].items():
        doc = old.freeze(); doc['questions'][0]['prompt'] = 'NEW_REGISTRY_' + actor
        replacement[content_hash(package)][actor] = FinaleQuestionScopes(package, doc)
    assert service(play, registry=replacement).get(pid, 1) == view
    assert service(play, registry={}).get(pid, 1) == view
    assert stored_binding(play) == before
    async def complete(messages, **params):
        wire = json.loads(messages[1].content)['context']
        assert 'NEW_REGISTRY_' not in canonical_json(wire)
        assert wire['questions'][0]['prompt'].startswith('SCOPE_b')
        return output(assessment(wire))
    play.sdk.chat_completion.side_effect = complete
    done = asyncio.run(service(play, registry=replacement).decide(pid, decision(view['revision'], 'b', 'SEAL_FINALE'), 1))
    assert done['last_ai_status'] == 'OK'
    assert service(play, registry={}).get(pid, 1) == done
    assert play.sdk.chat_completion.await_count == 1


def test_unacquired_basis_is_hidden_for_both_human_and_ai(play):
    view = enter(play, gated=True); pid = view['play_id']
    assert view['full_game']['finale']['questions'][0]['prompt'] == 'a-private-prompt'
    assert 'SCOPE_a' not in canonical_json(view) and 'HIDDEN_SCOPE_a' not in canonical_json(view)
    _, prepared = play.play._begin(pid, decision(view['revision'], 'b', 'SEAL_FINALE'), 1)
    assert prepared['source_context']['question_scopes'] == []
    wire = json.loads(prepared['messages'][1]['content'])['context']
    assert wire['questions'][0]['prompt'] == 'b-private-prompt'
    assert 'SCOPE_b' not in canonical_json(wire) and 'HIDDEN_SCOPE_b' not in canonical_json(wire)
    assert play.sdk.chat_completion.await_count == 0


def test_four_ai_scoped_receipts_seal_and_settle_with_identical_replay(play):
    view = enter(play); pid = view['play_id']
    view = play.play.table(pid, command(view['revision'], 'SEAL_FINALE', submission('a')), 1)
    async def complete(messages, **params): return output(assessment(json.loads(messages[1].content)['context']))
    play.sdk.chat_completion.side_effect = complete
    for actor in 'bcde':
        req = decision(view['revision'], actor, 'SEAL_FINALE')
        view = asyncio.run(play.play.decide(pid, req, 1))
        assert view['last_ai_status'] == 'OK' and asyncio.run(service(play, registry={}).decide(pid, req, 1)) == view
    view = play.play.act(pid, action_body(view['revision'], 'settle-scoped', 'SETTLE'), 1)
    assert view['settled'] and play.sdk.chat_completion.await_count == 4
    assert service(play, registry={}).get(pid, 1) == view
    results = [json.loads(e.event_json)['data'] for e in events(play) if e.kind == 'AI_RESULT']
    assert all(d['assessment']['schema_version'] == 'table-evidence-assessment/1.2' for d in results)
    assert all(d['assessment']['answers'][0]['selections'][0]['option_text'] for d in results)
    assert 'question_scopes' not in canonical_json(view) and 'assessment' not in canonical_json(view)


@pytest.mark.parametrize('policy', ['package-table-model/1.0', 'package-table-model/1.1',
    'package-table-model/1.2', EVIDENCE_MODEL_CONTRACT, LOCATED_MODEL_CONTRACT])
@pytest.mark.parametrize('prior_seal', [False, True])
def test_old_bindings_keep_original_human_ai_questions_and_event_hashes(play, policy, prior_seal):
    view = enter(play, policy=policy); pid = view['play_id']; binding = stored_binding(play)
    assert 'finale_question_scopes' not in binding
    async def complete(messages, **params):
        wire = json.loads(messages[1].content)['context']
        assert 'SCOPE_' not in canonical_json(wire) and 'question_scopes' not in wire
        return output(located_assessment(wire) if policy == LOCATED_MODEL_CONTRACT
                      else old_unknown(wire) if policy == EVIDENCE_MODEL_CONTRACT
                      else submission(wire['character']['id']))
    play.sdk.chat_completion.side_effect = complete
    if prior_seal: view = asyncio.run(play.play.decide(pid, decision(view['revision'], 'b', 'SEAL_FINALE'), 1))
    before = [(e.event_json, e.event_hash, e.state_hash) for e in events(play)]
    newer = service(play, legacy=policy if policy.endswith(('1.0', '1.1')) else 'package-table-model/1.0')
    assert newer.get(pid, 1) == view
    assert newer.get(pid, 1)['full_game']['finale']['questions'][0]['prompt'] == 'a-private-prompt'
    done = asyncio.run(newer.decide(pid, decision(view['revision'], 'c', 'SEAL_FINALE'), 1))
    assert done['last_ai_status'] == 'OK' and stored_binding(play) == binding
    assert [(e.event_json, e.event_hash, e.state_hash) for e in events(play)][:len(before)] == before


@pytest.mark.parametrize('policy', ['package-table-model/1.0', 'package-table-model/1.1',
    'package-table-model/1.2', EVIDENCE_MODEL_CONTRACT, LOCATED_MODEL_CONTRACT, SCOPED_MODEL_CONTRACT])
def test_new_default_never_redispatches_old_or_new_pending_scope_request(play, policy):
    view = enter(play, policy=policy); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    play.play._begin(pid, req, 1); saved = [e.event_json for e in events(play)]
    newer = service(play, registry={}, legacy=policy if policy.endswith(('1.0', '1.1')) else 'package-table-model/1.0')
    waiting = newer.get(pid, 1)
    assert asyncio.run(newer.decide(pid, req, 1)) == waiting
    assert [e.event_json for e in events(play)] == saved
    play.clock[0] += 301
    expired = asyncio.run(newer.decide(pid, req, 1))
    assert expired['last_ai_status'] == 'EXPIRED' and play.sdk.chat_completion.await_count == 0
    assert asyncio.run(newer.decide(pid, req, 1)) == expired


@pytest.mark.parametrize('change', ['missing_scopes', 'wrong_actor_key', 'wrong_doc_actor', 'wrong_package',
    'foreign_question', 'foreign_source', 'source_hash', 'prompt_hash', 'extra_doc', 'options', 'old_schema', 'old_policy'])
def test_new_binding_revalidates_frozen_scope_document_on_every_read(play, change):
    view = enter(play); binding = stored_binding(play); doc = binding['finale_question_scopes']['a']; q = doc['questions'][0]
    if change == 'missing_scopes': del binding['finale_question_scopes']
    elif change == 'wrong_actor_key': binding['finale_question_scopes']['unknown'] = binding['finale_question_scopes'].pop('a')
    elif change == 'wrong_doc_actor': doc['character_id'] = 'b'
    elif change == 'wrong_package': doc['package_hash'] = '0' * 64
    elif change == 'foreign_question': q['question_id'] = 'b-q'
    elif change == 'foreign_source': q['basis'][0]['id'] = 'initial-b'
    elif change == 'source_hash': q['basis'][0]['text_sha256'] = '0' * 64
    elif change == 'prompt_hash': q['original_prompt_sha256'] = '0' * 64
    elif change == 'extra_doc': doc['answer'] = ['red']
    elif change == 'options': q['options'] = []
    elif change == 'old_schema': binding['schema_version'] = 'package-text-play-binding/1.6'
    else: binding['table_policy'] = LOCATED_MODEL_CONTRACT
    row = play.db.query(ScriptPackagePlay).one()
    play.db.execute(update(ScriptPackagePlay).where(ScriptPackagePlay.id == row.id).values(
        binding_json=canonical_json(binding), binding_hash=content_hash(binding)))
    play.db.commit()
    with pytest.raises(PackagePlayError, match='SNAPSHOT_INVALID'): service(play).get(view['play_id'], 1)
    assert play.sdk.chat_completion.await_count == 0


@pytest.mark.parametrize('failure', ['invalid', 'unknown'])
def test_failed_scoped_output_replays_once_then_explicit_new_request_can_recover(play, failure):
    view = enter(play); pid = view['play_id']; req = decision(view['revision'], 'b', 'SEAL_FINALE')
    if failure == 'unknown': play.sdk.chat_completion.side_effect = RuntimeError('transport')
    else: play.sdk.chat_completion.return_value = output(submission('b'))
    failed = asyncio.run(play.play.decide(pid, req, 1))
    assert failed['last_ai_status'] == failure.upper()
    assert asyncio.run(service(play, registry={}).decide(pid, req, 1)) == failed
    assert play.sdk.chat_completion.await_count == 1
    original = events(play)[-1].event_json
    async def complete(messages, **params): return output(assessment(json.loads(messages[1].content)['context']))
    play.sdk.chat_completion.side_effect = complete
    done = asyncio.run(service(play, registry={}).decide(pid, decision(failed['revision'], 'b', 'SEAL_FINALE'), 1))
    assert done['last_ai_status'] == 'OK' and play.sdk.chat_completion.await_count == 2
    assert original in [e.event_json for e in events(play)]


@pytest.mark.parametrize('reason', ['model_disabled', 'budget_disabled', 'no_budget'])
def test_scoped_binding_cannot_bypass_current_disable_or_budget(play, reason):
    view = enter(play); before = len(events(play))
    if reason == 'model_disabled': play.model.settings = replace(play.model.settings, paid_calls_enabled=False)
    elif reason == 'budget_disabled': play.policy = replace(play.policy, paid_calls_enabled=False)
    else: play.policy = replace(play.policy, token_limit=0)
    blocked = service(play)
    with pytest.raises(PackagePlayError):
        asyncio.run(blocked.decide(view['play_id'], decision(view['revision'], 'b', 'SEAL_FINALE'), 1))
    assert len(events(play)) == before and play.sdk.chat_completion.await_count == 0

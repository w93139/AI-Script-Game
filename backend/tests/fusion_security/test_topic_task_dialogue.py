"""Frozen topic tasks: synthetic wire, event replay and old-model continuity."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from src.fusion.package_dialogue_model import TopicTaskPackageDialogueModel, dialogue_context_window
from src.fusion.package_play import PackagePlayService
from src.fusion.package_single_player import SinglePlayerContent
from src.fusion.package_validation import content_hash
from tests.fusion_security.test_package_runtime import runtime
from tests.fusion_security.test_package_play_store import play, start, events
from tests.fusion_security.test_package_full_play import full_package
from tests.fusion_security.test_single_player_topics import document, ask_topic
from tests.fusion_security.test_package_guided_flow import enter
from tests.fusion_security.test_full_play_store import command
from tests.fusion_security.test_full_play_decisions import output
from tests.fusion_security.test_conditional_topic_basis import SOURCE, ref, speech
from tests.fusion_security.test_ant_context_windows import case, ANT_V2


def plan(passages=None):
    return {'schema_version': 'topic-response-plan/1.0', 'instruction': '只核对当前问题，简短转述。',
            'sections': [{'id': 'answer', 'mode': 'REPORT', 'instruction': '说明钟楼的标记。',
                          'basis': [ref(passages=passages)]}]}


def service(play, policy='role-speech/1.11', db=None):
    return PackagePlayService(db if db is not None else play.db, play.publisher, play.model,
                             play.policy, lambda: play.clock[0], speech_policy=policy)


def bound_model(play, identifier):
    row = play.play._row(identifier, 1)
    package, binding = play.play._resolve(row)
    return play.play._replay(row, package, binding).response_model['schema_version']


def begin(play, channel='PUBLIC', policy='role-speech/1.11'):
    play.play = service(play, policy)
    package = full_package()
    package['knowledge'][1].update(text=SOURCE, retelling='MAY_RETELL')
    doc = document(package)
    doc['topics'][0]['responders'][0]['response_plans'] = {'initial': plan(), 'clarify': plan()}
    play.play.single_player_content = {content_hash(package): SinglePlayerContent(package, doc)}
    _, view = start(play, package)
    view = enter(play, view)
    if channel == 'PRIVATE':
        view = play.play.table(view['play_id'], command(view['revision'], 'START_CALL', {'peer_character_id': 'b'}), 1)
    return package, doc, view


def test_topic_task_wire_projects_original_passages_and_exact_ant_window():
    context, old, _ = case('scoped-dialogue')
    context.update(schema_version='package-dialogue-context/1.5', topic_response_task=plan())
    context['materials'][0].update(id='initial-b', text=SOURCE, retelling='MAY_RETELL')
    context['materials'] += [{**context['materials'][0], 'id': 'unrelated', 'text': '这份无关材料不可发送。'}]
    original = deepcopy(context)
    model = TopicTaskPackageDialogueModel(object(), old.settings)
    selected = dialogue_context_window(context, 98304, model.model_contract, ANT_V2)
    prepared = model.prepare(selected)
    wire = json.loads(prepared['messages'][1]['content'])['context']
    assert [m['id'] for m in wire['materials']] == ['initial-b']
    assert wire['materials'][0]['passages'] == [{'id': 'p0002', 'text': SOURCE.split('\n\n')[1]}]
    assert [d['id'] for d in wire['discussion']] == ['claim-3']
    assert wire['strategy_materials'] == []
    assert prepared['source_context']['materials'] == original['materials']
    assert context == original
    size = prepared['input_tokens'] - 4096
    model.settings = replace(model.settings, max_input_bytes=size)
    exact = dialogue_context_window(context, size, model.model_contract, ANT_V2)
    assert model.prepare(exact)['input_tokens'] == prepared['input_tokens']
    with pytest.raises(ValueError, match='REQUIRED_CONTEXT_TOO_LARGE'):
        dialogue_context_window(context, size - 1, model.model_contract, ANT_V2)


@pytest.mark.parametrize('channel', ['PUBLIC', 'PRIVATE'])
def test_topic_task_frozen_before_directory_change_reply_and_refresh(play, channel):
    package, doc, view = begin(play, channel)
    _, view = ask_topic(play, view, channel=channel)
    identifier = view['play_id']; request = view['single_player']['turns'][-1]['reply_request']
    doc['topics'][0]['responders'][0]['response_plans']['initial'] = plan(['p0001'])
    play.play.single_player_content = {content_hash(package): SinglePlayerContent(package, doc)}
    captured = []
    async def complete(messages, **params):
        wire = json.loads(messages[1].content)['context']; captured.append(wire)
        assert wire['schema_version'] == 'package-dialogue-context/1.5'
        assert wire['topic_response_task'] == plan()
        assert wire['materials'][0]['passages'][0]['id'] == 'p0002'
        assert SOURCE.split('\n\n')[0] not in json.dumps(wire, ensure_ascii=False)
        return output(speech('钟楼门口有蓝色的标识，其他情况仍待查证。'))
    play.sdk.chat_completion.side_effect = complete
    respond = play.play.reply_private if channel == 'PRIVATE' else play.play.respond
    view = asyncio.run(respond(identifier, request, 1))
    assert view['single_player']['turns'][-1]['status'] == 'OK'
    assert bound_model(play, identifier) == 'package-dialogue-model/1.14'
    assert asyncio.run(respond(identifier, request, 1)) == view
    assert play.sdk.chat_completion.await_count == 1
    if channel == 'PRIVATE': assert view['discussion']['entries'] == []
    old = [(e.event_json, e.request_json, e.state_hash) for e in events(play)]
    play.db.commit()
    with play.factory() as db:
        recovered = service(play, db=db)
        recovered.single_player_content = play.play.single_player_content
        assert recovered.get(identifier, 1) == view
    assert [(e.event_json, e.request_json, e.state_hash) for e in events(play)] == old


@pytest.mark.parametrize('channel', ['PUBLIC', 'PRIVATE'])
def test_topic_task_upgrade_preserves_bound_legacy_dialogue_model(play, channel):
    package, doc, view = begin(play, channel, 'role-speech/1.10')
    _, view = ask_topic(play, view, channel=channel)
    play.sdk.chat_completion.return_value = output(speech('钟楼门口有蓝色的标识，其他情况仍待查证。'))
    respond = play.play.reply_private if channel == 'PRIVATE' else play.play.respond
    view = asyncio.run(respond(view['play_id'], view['single_player']['turns'][-1]['reply_request'], 1))
    assert view['single_player']['turns'][-1]['status'] == 'OK'
    assert bound_model(play, view['play_id']) == 'package-dialogue-model/1.13'
    prior = [(e.event_json, e.request_json, e.state_hash) for e in events(play)]
    upgraded = service(play)
    upgraded.single_player_content = play.play.single_player_content
    play.play = upgraded
    assert upgraded.get(view['play_id'], 1) == view
    _, view = ask_topic(play, view, intent='clarify', channel=channel)
    async def complete(messages, **params):
        wire = json.loads(messages[1].content)['context']
        assert wire['schema_version'] == 'package-dialogue-context/1.4'
        assert 'topic_response_task' not in wire
        return output(speech('钟楼的蓝标记仍需和其他资料一起核实。'))
    play.sdk.chat_completion.side_effect = complete
    respond = upgraded.reply_private if channel == 'PRIVATE' else upgraded.respond
    view = asyncio.run(respond(view['play_id'], view['single_player']['turns'][-1]['reply_request'], 1))
    assert view['single_player']['turns'][-1]['status'] == 'OK'
    assert bound_model(play, view['play_id']) == 'package-dialogue-model/1.13'
    assert [(e.event_json, e.request_json, e.state_hash) for e in events(play)[:len(prior)]] == prior


@pytest.mark.parametrize('channel', ['PUBLIC', 'PRIVATE'])
def test_pending_old_request_reuses_original_prepared_after_upgrade(play, channel):
    _, _, view = begin(play, channel, 'role-speech/1.10')
    _, view = ask_topic(play, view, channel=channel)
    identifier = view['play_id']; request = view['single_player']['turns'][-1]['reply_request']
    pending, prepared = play.play._begin(identifier, request, 1)
    assert prepared['source_context']['schema_version'] == 'package-dialogue-context/1.4'
    old_events = [(e.event_json, e.request_json, e.state_hash) for e in events(play)]
    upgraded = service(play)
    upgraded.single_player_content = play.play.single_player_content
    play.play = upgraded
    respond = upgraded.reply_private if channel == 'PRIVATE' else upgraded.respond
    repeated = asyncio.run(respond(identifier, request, 1))
    assert repeated['single_player']['turns'][-1]['status'] == 'PENDING'
    assert play.sdk.chat_completion.await_count == 0
    play.sdk.chat_completion.return_value = output(speech('钟楼门口的蓝色标识可以继续核对。'))
    adapter = upgraded._full_response_adapter(prepared=prepared)
    assert adapter.model_contract == 'package-dialogue-model/1.13'
    result = asyncio.run(adapter.call(prepared))
    view = upgraded._finish(identifier, request['idempotency_key'], 1, result)
    assert view['single_player']['turns'][-1]['status'] == 'OK'
    assert asyncio.run(respond(identifier, request, 1)) == view
    assert play.sdk.chat_completion.await_count == 1
    assert [(e.event_json, e.request_json, e.state_hash) for e in events(play)[:len(old_events)]] == old_events

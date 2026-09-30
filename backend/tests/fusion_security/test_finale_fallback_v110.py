"""The 1.10 empty speech placeholder exists only in the public view."""
import asyncio

import pytest

from src.fusion.package_play import FINALE_110_DISPLAY_FALLBACK
from src.fusion.package_validation import content_hash
from tests.fusion_security.test_finale_motivation import (
    answer, enter_finale, events, output, play, runtime, service,
)
from tests.fusion_security.test_full_play_decisions import decision
from tests.fusion_security.test_full_play_store import command
from tests.fusion_security.test_package_play_store import action_body
from tests.fusion_security.test_structured_finale import submission


@pytest.mark.parametrize('model_answer', [
    {'text': '', 'basis': []},
    {'text': '我怀疑某人，9块银元仍待核对。',
     'basis': [{'collection': 'evidence', 'id': 'evidence-look-note'}]},
])
def test_v110_empty_or_invalid_is_display_only_with_marker(play, model_answer):
    play.test_finale_policy = 'finale-motivation/1.10'
    _, _, waiting = enter_finale(play)
    assert all(entry == {'character_id': entry['character_id'], 'text': ''}
               for entry in waiting['finale_speeches'])
    play.sdk.chat_completion.return_value = output(model_answer)
    done = asyncio.run(play.play.complete_finale_motivations(waiting['play_id'], 1))
    assert done['finale_motivation']['complete']
    assert all(entry == {'character_id': entry['character_id'],
                         'text': FINALE_110_DISPLAY_FALLBACK, 'fallback': True,
                         'fallback_source': 'generic'}
               for entry in done['finale_speeches'])
    row = play.play._row(waiting['play_id'], 1)
    package, binding = play.play._resolve(row)
    state = play.play._replay(row, package, binding)
    assert all(entry['text'] == '' and entry['status'] == 'EMPTY'
               for entry in state.finale_speeches)
    saved = [(entry.event_json, entry.event_hash, entry.state_hash) for entry in events(play)]
    assert saved[-1][2] == content_hash(state.state())
    assert '系统兜底' not in ''.join(entry.event_json for entry in events(play))
    assert service(play).get(waiting['play_id'], 1) == done
    assert [(entry.event_json, entry.event_hash, entry.state_hash) for entry in events(play)] == saved


def test_v110_nonempty_speech_is_unchanged(play):
    play.test_finale_policy = 'finale-motivation/1.10'
    _, _, waiting = enter_finale(play)
    value = answer('我怀疑某人，纸条仍有疑点。')
    play.sdk.chat_completion.return_value = output(value)
    done = asyncio.run(play.play.complete_finale_motivations(waiting['play_id'], 1))
    assert all(entry == {'character_id': entry['character_id'], 'text': value['text']}
               for entry in done['finale_speeches'])


@pytest.mark.parametrize('old_policy', ['finale-motivation/1.2',
                                         'finale-motivation/1.8',
                                         'finale-motivation/1.9'])
def test_old_empty_play_view_and_events_remain_identical(play, old_policy):
    play.test_finale_policy = old_policy
    _, _, waiting = enter_finale(play)
    play.sdk.chat_completion.return_value = output({'text': '', 'basis': []})
    old = asyncio.run(play.play.complete_finale_motivations(waiting['play_id'], 1))
    assert all(entry['text'] == '' and 'fallback' not in entry and 'fallback_source' not in entry
               for entry in old['finale_speeches'])
    saved = [(entry.event_json, entry.event_hash, entry.state_hash) for entry in events(play)]
    play.test_finale_policy = 'finale-motivation/1.10'
    assert service(play).get(waiting['play_id'], 1) == old
    assert [(entry.event_json, entry.event_hash, entry.state_hash) for entry in events(play)] == saved


def test_v110_fallback_is_absent_from_votes_and_scoring(play):
    play.test_finale_policy = 'finale-motivation/1.10'
    _, _, waiting = enter_finale(play)
    play.sdk.chat_completion.return_value = output({'text': '', 'basis': []})
    view = asyncio.run(play.play.complete_finale_motivations(waiting['play_id'], 1))
    view = play.play.table(view['play_id'],
                           command(view['revision'], 'SEAL_FINALE', submission('a', accusation='visitor')), 1)
    for actor in 'bcde':
        play.sdk.chat_completion.return_value = output(submission(
            actor, accusation='visitor' if actor in 'bc' else None))
        view = asyncio.run(play.play.decide(
            view['play_id'], decision(view['revision'], actor, 'SEAL_FINALE'), 1))
        if actor != 'e':
            assert 'vote_disclosure' not in view['full_game']['finale']
            assert all(entry['text'] == FINALE_110_DISPLAY_FALLBACK
                       and entry['fallback_source'] == 'generic'
                       for entry in view['finale_speeches'])
    assert all(entry['fallback'] for entry in view['finale_speeches'])
    disclosure = view['full_game']['finale']['vote_disclosure']
    assert disclosure[0]['motivation'] == '' and 'fallback' not in disclosure[0]
    assert [(entry['motivation'], entry['fallback'], entry['fallback_source'])
            for entry in disclosure[1:]] == [
                ('【系统兜底】我怀疑访客。', True, 'vote'), ('【系统兜底】我怀疑访客。', True, 'vote'),
                ('【系统兜底】我选择弃权。', True, 'vote'), ('【系统兜底】我选择弃权。', True, 'vote')]
    assert [(entry['text'], entry['fallback_source']) for entry in view['finale_speeches']] == [
        ('【系统兜底】我怀疑访客。', 'vote'), ('【系统兜底】我怀疑访客。', 'vote'),
        ('【系统兜底】我选择弃权。', 'vote'), ('【系统兜底】我选择弃权。', 'vote')]
    row = play.play._row(view['play_id'], 1)
    package, binding = play.play._resolve(row)
    engine = play.play._replay(row, package, binding).engine
    assert all(entry['motivation'] == '' for entry in engine.vote_disclosure([
        {'character_id': entry['character_id'], 'text': ''}
        for entry in view['finale_speeches']]))
    plain = engine._finale.result()
    with_original_empty = engine._finale.result([
        {'character_id': entry['character_id'], 'text': ''}
        for entry in view['finale_speeches']])
    assert {key: value for key, value in plain.items() if key != 'vote_disclosure'} == {
        key: value for key, value in with_original_empty.items() if key != 'vote_disclosure'}
    saved = [(entry.event_json, entry.event_hash, entry.state_hash) for entry in events(play)]
    assert service(play).get(view['play_id'], 1) == view
    assert [(entry.event_json, entry.event_hash, entry.state_hash) for entry in events(play)] == saved
    view = play.play.act(view['play_id'],
                         action_body(view['revision'], 'settle-v110', 'SETTLE'), 1)
    assert view['full_game']['result']['vote_disclosure'] == disclosure
    assert '系统兜底' not in ''.join(entry.event_json for entry in events(play))
    assert 'fallback_source' not in ''.join(entry.event_json for entry in events(play))

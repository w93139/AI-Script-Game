"""Finale 1.8 only corrects a uniquely identified basis collection."""
import asyncio

import pytest

from src.fusion.package_dialogue_model import (
    PROMPTS, AttributedFinaleMotivationOutput, _finale_context_model,
    _finale_output_model, validate_finale_motivation,
)
from tests.fusion_security.test_finale_attribution_v17 import attributed_context
from tests.fusion_security.test_finale_motivation import (
    answer, enter_finale, events, output, play, runtime, service,
)


def v18_context():
    return {**attributed_context(), 'schema_version': 'finale-motivation-context/1.8'}


def test_v18_keeps_v17_prompt_and_90_character_schema():
    assert PROMPTS['finale-motivation/1.8'] == PROMPTS['finale-motivation/1.7']
    assert _finale_output_model('finale-motivation/1.8') is AttributedFinaleMotivationOutput
    assert _finale_output_model('finale-motivation/1.8').model_json_schema()['properties']['text']['maxLength'] == 90
    assert _finale_context_model(v18_context()).__name__ == 'NormalizedFinaleMotivationContext'


def test_v18_normalizes_unique_discussion_and_evidence_matches():
    context = v18_context()
    value = {'text': '我怀疑阿杰，他说纸条仍待核对。',
             'basis': [{'collection': 'evidence', 'id': 'j-claim'}]}
    original = {'text': value['text'], 'basis': [dict(value['basis'][0])]}
    assert validate_finale_motivation(value, context) == {
        'text': value['text'], 'basis': [{'collection': 'discussion', 'id': 'j-claim'}]}
    assert value == original
    evidence = {'text': '我怀疑阿海，他说记录仍需核对。', 'basis': [
        {'collection': 'discussion', 'id': 'note'},
        {'collection': 'discussion', 'id': 'h-claim'}]}
    assert validate_finale_motivation(evidence, context)['basis'] == [
        {'collection': 'evidence', 'id': 'note'},
        {'collection': 'discussion', 'id': 'h-claim'}]


def test_v18_ambiguous_missing_and_existing_pairs_are_not_rewritten():
    context = v18_context()
    context['materials'].append({'collection': 'evidence', 'id': 'j-claim', 'text': '另一件已公开物证。'})
    text = '我怀疑阿杰，他说纸条仍待核对。'
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_INVALID'):
        validate_finale_motivation({'text': text, 'basis': [
            {'collection': 'knowledge', 'id': 'j-claim'}]}, context)
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_INVALID'):
        validate_finale_motivation({'text': text, 'basis': [
            {'collection': 'evidence', 'id': 'unknown'}]}, context)
    with pytest.raises(ValueError, match='SPEAKER_UNSUPPORTED'):
        validate_finale_motivation({'text': text, 'basis': [
            {'collection': 'evidence', 'id': 'j-claim'}]}, context)


def test_v18_deduplicates_after_normalization_and_preserves_empty_rules():
    context = v18_context()
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_INVALID'):
        validate_finale_motivation({'text': '我怀疑阿杰，他说纸条仍待核对。', 'basis': [
            {'collection': 'evidence', 'id': 'j-claim'},
            {'collection': 'discussion', 'id': 'j-claim'}]}, context)
    assert validate_finale_motivation({'text': '', 'basis': []}, context) == {'text': '', 'basis': []}
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_INVALID'):
        validate_finale_motivation({'text': '', 'basis': [
            {'collection': 'evidence', 'id': 'j-claim'}]}, context)


def test_v17_behavior_stays_invalid_and_named_mismatch_still_rejects_in_v18():
    value = {'text': '我怀疑阿杰，他说纸条仍待核对。',
             'basis': [{'collection': 'evidence', 'id': 'j-claim'}]}
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_INVALID'):
        validate_finale_motivation(value, attributed_context())
    wrong_speaker = {**value, 'text': '我怀疑阿海，他说纸条仍待核对。'}
    with pytest.raises(ValueError, match='SPEAKER_UNSUPPORTED'):
        validate_finale_motivation(wrong_speaker, v18_context())


def test_v18_new_binding_does_not_replay_old_v17_game(play):
    play.test_finale_policy = 'finale-motivation/1.7'
    _, _, old = enter_finale(play)
    play.sdk.chat_completion.return_value = output(answer())
    old_done = asyncio.run(play.play.complete_finale_motivations(old['play_id'], 1))
    old_events = [(item.event_json, item.event_hash, item.state_hash) for item in events(play)]
    play.test_finale_policy = 'finale-motivation/1.8'
    newer = service(play)
    assert newer.get(old['play_id'], 1) == old_done
    assert asyncio.run(newer.complete_finale_motivations(old['play_id'], 1)) == old_done
    assert [(item.event_json, item.event_hash, item.state_hash) for item in events(play)] == old_events
    assert play.sdk.chat_completion.await_count == 4


def test_v18_new_play_binds_its_own_policy(play):
    play.test_finale_policy = 'finale-motivation/1.8'
    _, _, current = enter_finale(play)
    row = play.play._row(current['play_id'], 1)
    _, binding = play.play._resolve(row)
    assert binding['finale_motivation_policy'] == 'finale-motivation/1.8'

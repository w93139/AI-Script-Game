"""New finale grammar and frozen-policy continuation, with synthetic sources."""
import asyncio
from copy import deepcopy
import json

import pytest

from src.fusion.package_dialogue_model import (
    PROMPTS, FinaleMotivationOutput, SingleSentenceFinaleMotivationOutput,
    finale_motivation_input_size, validate_finale_motivation,
)
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_finale_motivation import (
    play, runtime, enter_finale, service, answer, output, events, careful_context,
)


@pytest.mark.parametrize('text', [
    '我怀疑甲。纸条值得核对。', '我怀疑甲；纸条值得核对。',
    '我怀疑甲\n纸条值得核对。', '我怀疑甲！纸条值得核对。',
])
def test_single_sentence_is_declared_in_wire_schema_and_locally_enforced(text):
    schema = SingleSentenceFinaleMotivationOutput.model_json_schema()
    assert schema['properties']['text']['maxLength'] == 60
    assert schema['properties']['text']['pattern']
    raw = {'text': text, 'basis': [{'collection': 'evidence', 'id': 'note'}]}
    with pytest.raises(ValueError):
        validate_finale_motivation(raw, careful_context('1.3'))


@pytest.mark.parametrize('text', [
    '我怀疑甲，登记信息仍待核对。', '我认为甲的登记信息仍待核对',
    '我暂时怀疑甲，登记信息仍待核对。',
])
def test_single_sentence_retains_short_qualified_outputs(text):
    raw = {'text': text, 'basis': [{'collection': 'evidence', 'id': 'note'}]}
    assert validate_finale_motivation(raw, careful_context('1.3')) == raw
    assert validate_finale_motivation({'text': '', 'basis': []}, careful_context('1.3')) == {'text': '', 'basis': []}


@pytest.mark.parametrize('text,error', [
    ('我怀疑甲，绝对是他的东西。', 'CERTAINTY_UNSUPPORTED'),
    ('我怀疑甲，他精神不佳，证词可信度低。', 'CREDIBILITY_UNSUPPORTED'),
    ('我怀疑甲，他见过那位旅客。', 'ATTRIBUTION_REQUIRED'),
])
def test_new_grammar_keeps_careful_semantic_boundaries(text, error):
    raw = {'text': text, 'basis': [{'collection': 'discussion', 'id': 'claim-old'}]}
    with pytest.raises(ValueError, match=error):
        validate_finale_motivation(raw, careful_context('1.3'))


@pytest.mark.parametrize('version', ['1.3', '1.4'])
def test_new_finale_uses_versioned_schema_prompt_and_exact_input_meter(play, version):
    play.test_finale_policy = 'finale-motivation/' + version
    _, _, view = enter_finale(play)
    row = play.play._row(view['play_id'], 1)
    package, binding = play.play._resolve(row)
    state = play.play._replay(row, package, binding)
    before = deepcopy(state.engine.state())
    context = play.play._finale_context(state, binding, 'b')
    prepared = play.play.finale_model.prepare(context)
    assert prepared['input_tokens'] == finale_motivation_input_size(context, binding['model']) + 4096
    assert prepared['params']['response_format']['json_schema']['schema'] == SingleSentenceFinaleMotivationOutput.model_json_schema()
    assert play.play.finale_model.metadata()['schema_hash'] != content_hash(FinaleMotivationOutput.model_json_schema())
    async def sdk(messages, **params):
        frozen = json.loads(messages[1].content)['context']
        assert frozen['schema_version'] == 'finale-motivation-context/' + version
        assert '句号只可放在末尾' in messages[0].content
        assert 'PRIVATE_BOOK_' not in canonical_json(frozen)
        assert 'SYSTEM_TRUTH' not in canonical_json(frozen)
        return output(answer())
    play.sdk.chat_completion.side_effect = sdk
    done = asyncio.run(play.play.complete_finale_motivations(view['play_id'], 1))
    assert all(e['text'] == answer()['text'] for e in done['finale_speeches'])
    assert play.play._replay(row, package, binding).engine.state() == before
    assert service(play).get(view['play_id'], 1) == done
    assert asyncio.run(service(play).complete_finale_motivations(view['play_id'], 1)) == done
    assert play.sdk.chat_completion.await_count == 4


@pytest.mark.parametrize('old_policy', ['finale-motivation/1.0', 'finale-motivation/1.1', 'finale-motivation/1.2', 'finale-motivation/1.3'])
@pytest.mark.parametrize('pending', [False, True])
def test_new_default_continues_old_unfinished_game_with_frozen_wire_policy(play, old_policy, pending):
    play.test_finale_policy = old_policy
    _, _, view = enter_finale(play)
    if pending:
        key, prepared = play.play._begin_finale_motivation(view['play_id'], 'b', 1)
        assert prepared
    before = [(e.event_json, e.event_hash, e.state_hash) for e in events(play)]
    play.test_finale_policy = 'finale-motivation/1.4'
    newer = service(play)
    async def sdk(messages, **params):
        assert messages[0].content == PROMPTS[old_policy]
        expected = SingleSentenceFinaleMotivationOutput if old_policy == 'finale-motivation/1.3' else FinaleMotivationOutput
        assert params['response_format']['json_schema']['schema'] == expected.model_json_schema()
        assert json.loads(messages[1].content)['context']['schema_version'] == old_policy.replace('motivation/', 'motivation-context/')
        return output(answer())
    play.sdk.chat_completion.side_effect = sdk
    if pending:
        waiting = asyncio.run(newer.complete_finale_motivations(view['play_id'], 1))
        assert waiting['pending_ai'] and play.sdk.chat_completion.await_count == 0
        assert [(e.event_json, e.event_hash, e.state_hash) for e in events(play)] == before
        play.clock[0] += 301
    done = asyncio.run(newer.complete_finale_motivations(view['play_id'], 1))
    assert done['finale_motivation']['complete']
    assert play.sdk.chat_completion.await_count == (3 if pending else 4)
    assert all(e['text'] == answer()['text'] for e in done['finale_speeches'][1 if pending else 0:])
    assert [(e.event_json, e.event_hash, e.state_hash) for e in events(play)][:len(before)] == before
    assert newer.get(view['play_id'], 1) == done


def test_new_default_does_not_bypass_current_model_disable_for_old_game(play):
    _, _, view = enter_finale(play)
    play.test_finale_policy = 'finale-motivation/1.3'
    newer = service(play)
    newer.finale_model.available = False
    done = asyncio.run(newer.complete_finale_motivations(view['play_id'], 1))
    assert done['finale_motivation']['complete']
    assert all(e['text'] == '' for e in done['finale_speeches'])
    assert play.sdk.chat_completion.await_count == 0

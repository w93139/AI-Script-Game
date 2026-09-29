"""Finale 1.10 adds literal source gates without changing prior bindings."""
import asyncio
from copy import deepcopy
from hashlib import sha256

import pytest

from src.fusion.package_dialogue_model import (
    PROMPTS, _finale_context_model, _finale_output_model,
    validate_finale_motivation,
)
from src.fusion.package_validation import content_hash
from tests.fusion_security.test_finale_location_prompt_v19 import v19_context
from tests.fusion_security.test_finale_motivation import (
    answer, enter_finale, events, output, play, runtime, service,
)


def v110_context():
    return {**v19_context(), 'schema_version': 'finale-motivation-context/1.10'}


def cited(text, *refs):
    return {'text': text, 'basis': [
        {'collection': collection, 'id': ref_id} for collection, ref_id in refs]}


def test_v110_prompt_schema_and_prior_v19_hashes_are_frozen():
    assert PROMPTS['finale-motivation/1.10'].startswith(PROMPTS['finale-motivation/1.9'])
    assert '数字或年份' in PROMPTS['finale-motivation/1.10']
    assert '点名某人说、称、证实' in PROMPTS['finale-motivation/1.10']
    assert _finale_output_model('finale-motivation/1.10') is _finale_output_model('finale-motivation/1.9')
    assert _finale_context_model(v110_context()).model_json_schema()['properties']['schema_version']['const'] == 'finale-motivation-context/1.10'
    assert sha256(PROMPTS['finale-motivation/1.9'].encode()).hexdigest() == 'f14fd80a4cfeb9db89c164637681fc3fea3a15f9b4247d2f3409ec95acf2a659'
    assert content_hash(_finale_output_model('finale-motivation/1.9').model_json_schema()) == '8d67591883b7e81b8060e2f673a8edccbb268e12287e9e35cf1b22c3741a1534'
    assert content_hash(_finale_context_model(v19_context()).model_json_schema()) == '6b8cd6ab05204c2142892566b572b95d7ea656f8dbd029d0a906ff75e9e32414'


def test_v110_rejects_uncited_number_and_year_but_preserves_v19():
    for detail in ('1912年', '光绪三十年', '9块银元'):
        value = cited(f'我怀疑阿杰，他说{detail}仍待核对。', ('discussion', 'j-claim'))
        assert validate_finale_motivation(deepcopy(value), v19_context()) == value
        with pytest.raises(ValueError, match='FINALE_MOTIVATION_NUMBER_UNSUPPORTED'):
            validate_finale_motivation(value, v110_context())


def test_v110_requires_the_cited_source_to_contain_a_relative_year_phrase():
    context = v110_context()
    context['discussion'][1]['text'] = '1912年记载一件旧事。'
    value = cited('我怀疑阿杰，他说此事发生于1912年之后仍待核对。',
                  ('discussion', 'j-claim'))
    assert validate_finale_motivation(deepcopy(value), v19_context() | {
        'discussion': deepcopy(context['discussion'])}) == value
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_NUMBER_UNSUPPORTED'):
        validate_finale_motivation(value, context)
    context['discussion'][1]['text'] += '此事发生于1912年之后。'
    assert validate_finale_motivation(value, context) == value
    spaced = cited('我怀疑阿杰，他说此事发生于1912 年之后仍待核对。',
                   ('discussion', 'j-claim'))
    assert validate_finale_motivation(spaced, context) == spaced


def test_v110_does_not_accept_a_number_only_as_part_of_another_number():
    context = v110_context()
    context['discussion'][1]['text'] = '记录中有19块银元。'
    value = cited('我怀疑阿杰，他说9块银元仍待核对。',
                  ('discussion', 'j-claim'))
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_NUMBER_UNSUPPORTED'):
        validate_finale_motivation(value, context)


def test_v110_accepts_cited_numbers_years_and_named_speaker():
    context = v110_context()
    context['discussion'][1]['text'] = '我说光绪三十年（1904年）有9块银元，纸条仍待核对。'
    value = cited('我怀疑阿杰，阿杰说光绪三十年（1904年）有9块银元仍待核对。',
                  ('evidence', 'j-claim'))
    assert validate_finale_motivation(value, context)['basis'] == [
        {'collection': 'discussion', 'id': 'j-claim'}]
    context['materials'][0]['text'] += '吉叔证实记录仍待核对。'
    value = cited('我怀疑阿杰，吉叔证实记录仍待核对。',
                  ('discussion', 'j-claim'), ('evidence', 'note'))
    assert validate_finale_motivation(value, context) == value


def test_v110_rejects_uncited_npc_name_but_keeps_cited_role_and_empty():
    value = cited('我怀疑阿杰，管家吉叔证实纸条仍待核对。',
                  ('discussion', 'j-claim'))
    assert validate_finale_motivation(deepcopy(value), v19_context()) == value
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_NAMED_SPEAKER_UNSUPPORTED'):
        validate_finale_motivation(value, v110_context())
    self_claim = cited('我怀疑阿杰，吉叔自称纸条仍待核对。',
                       ('discussion', 'j-claim'))
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_NAMED_SPEAKER_UNSUPPORTED'):
        validate_finale_motivation(self_claim, v110_context())
    ordinary_name = cited('我怀疑阿杰，王小明说纸条仍待核对。',
                          ('discussion', 'j-claim'))
    with pytest.raises(ValueError, match='FINALE_MOTIVATION_NAMED_SPEAKER_UNSUPPORTED'):
        validate_finale_motivation(ordinary_name, v110_context())
    context = v110_context()
    context['discussion'][1]['text'] += '王小明说纸条仍待核对。'
    assert validate_finale_motivation(ordinary_name, context) == ordinary_name
    supported = cited('我怀疑阿杰，阿杰说纸条仍待核对。',
                      ('discussion', 'j-claim'))
    assert validate_finale_motivation(supported, v110_context()) == supported
    assert validate_finale_motivation({'text': '', 'basis': []}, v110_context()) == {
        'text': '', 'basis': []}


def test_v110_does_not_treat_pronoun_as_a_named_person():
    value = cited('我怀疑阿杰，因为他说纸条仍待核对。',
                  ('discussion', 'j-claim'))
    assert validate_finale_motivation(value, v110_context()) == value
    generic = cited('我怀疑阿杰，因为有人声称纸条仍待核对。',
                    ('discussion', 'j-claim'))
    assert validate_finale_motivation(generic, v110_context()) == generic


def test_v110_new_binding_keeps_old_v19_play_and_events(play):
    play.test_finale_policy = 'finale-motivation/1.9'
    _, _, old = enter_finale(play)
    play.sdk.chat_completion.return_value = output(answer())
    old_done = asyncio.run(play.play.complete_finale_motivations(old['play_id'], 1))
    old_events = [(item.event_json, item.event_hash, item.state_hash) for item in events(play)]
    play.test_finale_policy = 'finale-motivation/1.10'
    newer = service(play)
    assert newer.get(old['play_id'], 1) == old_done
    assert asyncio.run(newer.complete_finale_motivations(old['play_id'], 1)) == old_done
    assert [(item.event_json, item.event_hash, item.state_hash) for item in events(play)] == old_events
    assert play.sdk.chat_completion.await_count == 4


def test_v110_new_play_binds_new_context(play):
    play.test_finale_policy = 'finale-motivation/1.10'
    _, _, view = enter_finale(play)
    row = play.play._row(view['play_id'], 1)
    _, binding = play.play._resolve(row)
    assert binding['finale_motivation_policy'] == 'finale-motivation/1.10'
    state = play.play._replay(row, *play.play._resolve(row))
    context = play.play._finale_context(state, binding, 'b')
    assert context['schema_version'] == 'finale-motivation-context/1.10'

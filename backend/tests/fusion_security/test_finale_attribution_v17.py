"""Finale 1.7 adds length and speaker checks without changing old contracts."""
import asyncio
from copy import deepcopy
from hashlib import sha256

import pytest

from src.fusion.package_dialogue_model import (
    PROMPTS, AttributedFinaleMotivationOutput,
    _finale_context_model, _finale_output_model, finale_motivation_input_size,
    validate_finale_motivation,
)
from src.fusion.package_validation import content_hash
from tests.fusion_security.test_finale_motivation import (
    answer, enter_finale, events, output, play, runtime, service,
)


def attributed_context():
    return {
        'schema_version': 'finale-motivation-context/1.7',
        'character': {'id': 'T', 'name': '唐小姐'},
        'public_characters': [
            {'id': 'T', 'name': '唐小姐'}, {'id': 'H', 'name': '阿海'},
            {'id': 'J', 'name': '阿杰'}],
        'materials': [{'collection': 'evidence', 'id': 'note', 'text': '登记记录仍待核对。'}],
        'discussion': [
            {'id': 'h-claim', 'speaker': 'H', 'text': '我说登记记录仍待核对。'},
            {'id': 'j-claim', 'speaker': 'J', 'text': '我说纸条仍待核对。'}],
        'evidence_origins': [{'id': 'note', 'labels': ['登记处']}],
    }


def cited(text, claim='h-claim'):
    return {'text': text, 'basis': [{'collection': 'discussion', 'id': claim}]}


def test_v17_accepts_66_character_single_sentence_and_keeps_90_cap():
    schema = AttributedFinaleMotivationOutput.model_json_schema()
    assert schema['properties']['text']['maxLength'] == 90
    assert '不超过90字' in PROMPTS['finale-motivation/1.7']
    assert '不超过60字' not in PROMPTS['finale-motivation/1.7']
    assert schema['properties']['text']['pattern'] == (
        r'^[^。！？!?；;\r\n]*[。！？!?]?$')
    text = '我怀疑阿海，他说记录仍需核对，' + '相关记录' * 12 + '再查。'
    assert len(text) == 66
    assert validate_finale_motivation(cited(text), attributed_context()) == cited(text)
    with pytest.raises(ValueError):
        validate_finale_motivation(cited(text + '。'), attributed_context())
    with pytest.raises(ValueError):
        validate_finale_motivation(cited('我怀疑阿海，' + '线索' * 45 + '。'), attributed_context())


def test_v17_rejects_named_role_without_its_cited_discussion_and_keeps_empty():
    context = attributed_context()
    with pytest.raises(ValueError, match='SPEAKER_UNSUPPORTED'):
        validate_finale_motivation(cited('我怀疑阿海，阿杰所说的记录仍需核对。'), context)
    with pytest.raises(ValueError, match='SPEAKER_UNSUPPORTED'):
        validate_finale_motivation(cited('我怀疑阿海，登记记录仍需核对。', 'j-claim'), context)
    with pytest.raises(ValueError, match='SPEAKER_UNSUPPORTED'):
        validate_finale_motivation({'text': '我怀疑阿海，登记记录仍需核对。',
                                   'basis': [{'collection': 'evidence', 'id': 'note'}]}, context)
    assert validate_finale_motivation(cited('我怀疑阿海，他说记录仍需核对。'), context) == (
        cited('我怀疑阿海，他说记录仍需核对。'))
    assert validate_finale_motivation({'text': '', 'basis': []}, context) == (
        {'text': '', 'basis': []})


def test_prior_prompt_output_and_context_schema_hashes_are_frozen():
    expected = {
        '1.0': ('f9044c0a0e790c5ef33aae1cd3e744990f328f59aa773cd5935cb2a93958d14a',
                '70bb3d0809b40ca527db6e0a0198716b6fcdab3dcee66deee6ea6156637779b4',
                '97d51eca444ca1dc553d7f2afe3917073c96d3f335d7778700b35b7b2887d0b0'),
        '1.1': ('2788a851480c7680fd2e560cfd15f4a01d8995c35f8e7c844e299960bcec90a2',
                '70bb3d0809b40ca527db6e0a0198716b6fcdab3dcee66deee6ea6156637779b4',
                '53ad9a7c1a2426d768157c991c2d1b75afc0d821d4e3fdaad6b00393e08401a4'),
        '1.2': ('9c7a03a5d10409de496109db62ba4e419380a3a90e89ca42e8a94ea9b7ca6f9e',
                '70bb3d0809b40ca527db6e0a0198716b6fcdab3dcee66deee6ea6156637779b4',
                'e88cafa667397d08794c9128cb20b1c758b9646d8a1a5873ae1c6aca00138de1'),
        '1.3': ('d52833c8b31d0eff2e4a190322398ab9843614d9f75883194ef11acb861022f1',
                'eed3b22723ba19602ac834e81555064f906d586bfa2d8067ab77c0ae530f3fa7',
                '8c458194940e219fceaf4ab08bdb6495f2284bb3b2a4d4bf5aaefe17a1116811'),
        '1.4': ('566f057d2c6c373ee51681cd3942a45fbf3a6954883eddca99ab6645a91669dd',
                'eed3b22723ba19602ac834e81555064f906d586bfa2d8067ab77c0ae530f3fa7',
                '8e9f036ac4114e61aa7d72ba35475c61454b1c8bc0c7f9f0838ca6a5cdba3249'),
        '1.5': ('812e7c442873e340127fde2e5d76855b4954a5b6f9f5e5e71ad52af7e55ef10a',
                '9d8805f98e76feca0d0f6c609f7e53d4dda0f745b46f167fc2499919ebdaca0d',
                '977c0d3f06d4838e18e5ab5d93afc826e2ca431526e6410c37bef5eaf914d2cd'),
        '1.6': ('fd49b7b5a2c4cd6891c80b2370e06da61b4e62b42fa8aecde54ffdb830cb63ea',
                'de00361a7bdd317971a71dd4eef1776d46170ea56b64844b6477d6c740a063b6',
                'c20801f0fad1772110c0230c2a89610608d1c88181767207a1aba751d882dba0'),
        '1.7': ('a4664c89d3bc0f88e906827540f90d9e6bddb264ea2789c79e25b173df51d99f',
                '8d67591883b7e81b8060e2f673a8edccbb268e12287e9e35cf1b22c3741a1534',
                'dddd44a7d82cebf8cdca009a8555172e23adbabc3d28ac77813878510693c081'),
        '1.8': ('a4664c89d3bc0f88e906827540f90d9e6bddb264ea2789c79e25b173df51d99f',
                '8d67591883b7e81b8060e2f673a8edccbb268e12287e9e35cf1b22c3741a1534',
                'e276cddb0bb9d1ecd7ed490b7de6a5022a3b766da20cb8fbe01b2f952b5f089e'),
    }
    for version, hashes in expected.items():
        policy = 'finale-motivation/' + version
        context = {'schema_version': 'finale-motivation-context/' + version}
        assert sha256(PROMPTS[policy].encode()).hexdigest() == hashes[0]
        assert content_hash(_finale_output_model(policy).model_json_schema()) == hashes[1]
        assert content_hash(_finale_context_model(context).model_json_schema()) == hashes[2]


def test_v17_new_binding_and_old_completed_game_stay_frozen(play):
    play.test_finale_policy = 'finale-motivation/1.2'
    _, _, old = enter_finale(play)
    play.sdk.chat_completion.return_value = output(answer())
    old_done = asyncio.run(play.play.complete_finale_motivations(old['play_id'], 1))
    old_events = [(item.event_json, item.event_hash, item.state_hash) for item in events(play)]
    play.test_finale_policy = 'finale-motivation/1.7'
    newer = service(play)
    assert newer.get(old['play_id'], 1) == old_done
    assert asyncio.run(newer.complete_finale_motivations(old['play_id'], 1)) == old_done
    assert [(item.event_json, item.event_hash, item.state_hash) for item in events(play)] == old_events
    assert play.sdk.chat_completion.await_count == 4


def test_v17_actual_service_uses_public_cast_and_exact_wire_size(play):
    play.test_finale_policy = 'finale-motivation/1.7'
    _, _, view = enter_finale(play)
    row = play.play._row(view['play_id'], 1)
    package, binding = play.play._resolve(row)
    assert binding['finale_motivation_policy'] == 'finale-motivation/1.7'
    state = play.play._replay(row, package, binding)
    context = play.play._finale_context(state, binding, 'b')
    assert context['schema_version'] == 'finale-motivation-context/1.7'
    assert context['public_characters'] == [
        {'id': item['id'], 'name': item['name']} for item in package['characters']]
    model = play.play.finale_model
    prepared = model.prepare(context)
    assert prepared['input_tokens'] == finale_motivation_input_size(context, binding['model']) + 4096
    assert prepared['params']['response_format']['json_schema']['schema'] == (
        AttributedFinaleMotivationOutput.model_json_schema())
    assert deepcopy(state.engine.state()) == state.engine.state()

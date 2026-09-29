"""Finale 1.9 changes only the place-citation instruction and new binding."""
import asyncio
from copy import deepcopy
from hashlib import sha256

import pytest

from src.fusion.package_dialogue_model import (
    PROMPTS, _finale_context_model, _finale_output_model,
    validate_finale_motivation,
)
from src.fusion.package_validation import content_hash
from tests.fusion_security.test_finale_basis_normalization_v18 import v18_context
from tests.fusion_security.test_finale_motivation import (
    answer, enter_finale, events, output, play, runtime, service,
)


def v19_context():
    return {**v18_context(), 'schema_version': 'finale-motivation-context/1.9'}


def test_v19_prompt_requires_cited_evidence_for_every_named_place():
    prompt = PROMPTS['finale-motivation/1.9']
    assert prompt.startswith(PROMPTS['finale-motivation/1.8'])
    assert '若 text 提到地点，basis 必须包含该地点所在的物证条目' in prompt
    assert 'evidence_origins 中的标签必须含这个地点' in prompt
    assert '无法引用对应物证时省略地点' in prompt
    assert sha256(prompt.encode()).hexdigest() != sha256(PROMPTS['finale-motivation/1.8'].encode()).hexdigest()
    assert content_hash(_finale_output_model('finale-motivation/1.9').model_json_schema()) == (
        content_hash(_finale_output_model('finale-motivation/1.8').model_json_schema()))
    assert _finale_context_model(v19_context()).__name__ == 'LocationCitedFinaleMotivationContext'


@pytest.mark.parametrize('value', [
    {'text': '我怀疑阿杰，他说纸条仍待核对。',
     'basis': [{'collection': 'evidence', 'id': 'j-claim'}]},
    {'text': '我怀疑阿海，他说登记处的记录仍需核对。',
     'basis': [{'collection': 'discussion', 'id': 'h-claim'}]},
    {'text': '我怀疑阿海，他说登记处的记录仍需核对。',
     'basis': [{'collection': 'discussion', 'id': 'h-claim'},
               {'collection': 'evidence', 'id': 'note'}]},
    {'text': '我怀疑阿海，他说纸条仍待核对。',
     'basis': [{'collection': 'evidence', 'id': 'j-claim'}]},
    {'text': '', 'basis': []},
])
def test_v19_validation_matches_v18_including_normalization_location_and_empty(value):
    outcomes = []
    for context in (v18_context(), v19_context()):
        try:
            outcomes.append(('ACCEPTED', validate_finale_motivation(deepcopy(value), context)))
        except ValueError as exc:
            outcomes.append(('REJECTED', str(exc)))
    assert outcomes[0] == outcomes[1]


def test_v19_new_binding_does_not_change_old_v18_replay(play):
    play.test_finale_policy = 'finale-motivation/1.8'
    _, _, old = enter_finale(play)
    play.sdk.chat_completion.return_value = output(answer())
    old_done = asyncio.run(play.play.complete_finale_motivations(old['play_id'], 1))
    old_events = [(item.event_json, item.event_hash, item.state_hash) for item in events(play)]
    play.test_finale_policy = 'finale-motivation/1.9'
    newer = service(play)
    assert newer.get(old['play_id'], 1) == old_done
    assert asyncio.run(newer.complete_finale_motivations(old['play_id'], 1)) == old_done
    assert [(item.event_json, item.event_hash, item.state_hash) for item in events(play)] == old_events
    assert play.sdk.chat_completion.await_count == 4


def test_v19_new_play_binds_its_own_policy(play):
    play.test_finale_policy = 'finale-motivation/1.9'
    _, _, view = enter_finale(play)
    row = play.play._row(view['play_id'], 1)
    _, binding = play.play._resolve(row)
    assert binding['finale_motivation_policy'] == 'finale-motivation/1.9'
    state = play.play._replay(row, *play.play._resolve(row))
    context = play.play._finale_context(state, binding, 'b')
    assert context['schema_version'] == 'finale-motivation-context/1.9'

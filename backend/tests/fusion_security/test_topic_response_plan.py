"""Authored task scoping preserves exact source spans and rejects missing basis."""
from copy import deepcopy

import pytest

from src.fusion.speech_passages import passage_wire_context
from src.fusion.topic_response_plan import (
    PLAN_POLICY, TopicResponsePlan, project_topic_wire,
    validate_topic_plan, validate_topic_plan_output,
)


def basis(identifier='own', passages=None, collection='knowledge'):
    return {'collection': collection, 'id': identifier, 'passage_ids': passages or ['p0002']}


def plan():
    return {'schema_version': PLAN_POLICY, 'instruction': '只回答这一问题。', 'sections': [
        {'id': 'known', 'mode': 'REPORT', 'instruction': '保留未知时间。', 'basis': [basis()]},
        {'id': 'possibility', 'mode': 'INFERENCE', 'instruction': '明确只是怀疑。',
         'basis': [basis('notice', ['p0001'], 'evidence')]},
    ]}


def context():
    return {'materials': [
        {'collection': 'knowledge', 'id': 'own', 'text': '早晨醒来。\n\n不知何时，又醒过一次。\n\n傍晚听见铃声。',
         'retelling': 'MAY_RETELL', 'kind': 'FACT'},
        {'collection': 'evidence', 'id': 'notice', 'text': '柜门似乎被人碰过。', 'kind': 'FACT'},
        {'collection': 'knowledge', 'id': 'other', 'text': '另一件获准但无关的事情。', 'kind': 'FACT'},
    ], 'discussion': [
        {'id': 'old', 'text': '先前的话题。'}, {'id': 'question', 'text': '你醒来几次？'},
    ], 'reply_to': 'question', 'strategy_materials': [{'id': 'goal', 'text': '私有策略。'}],
        'history_window': {'policy': 'full-play-context-window/1.0', 'omitted_count': 7},
        'topic_response_task': plan()}


def sources(c):
    return {(m['collection'], m['id']): m for m in c['materials']}


def speech():
    return {'segments': [{'mode': s['mode'], 'text': '待核实的自然表达。', 'basis': deepcopy(s['basis'])}
                         for s in plan()['sections']]}


def test_plan_is_strict_source_bound_and_returns_an_independent_copy():
    c = context(); task = plan(); before = deepcopy(task)
    validated = validate_topic_plan(task, sources(c))
    assert TopicResponsePlan.model_validate(task).model_dump() == validated == before
    validated['sections'][0]['basis'][0]['passage_ids'].append('p0001')
    assert task == before


@pytest.mark.parametrize('bad', [
    'version', 'extra', 'empty_instruction', 'long_instruction', 'control_instruction',
    'empty_sections', 'many_sections', 'duplicate_sections', 'section_extra', 'question_mode',
    'empty_section_instruction', 'long_section_instruction', 'empty_basis', 'many_basis',
    'duplicate_basis', 'foreign_source', 'discussion_source', 'unknown_passage', 'duplicate_passage',
    'empty_passages', 'many_passages', 'basis_extra',
])
def test_invalid_plan_is_rejected(bad):
    c = context(); task = plan(); section = task['sections'][0]; ref = section['basis'][0]
    if bad == 'version': task['schema_version'] = 'topic-response-plan/9.0'
    elif bad == 'extra': task['extra'] = True
    elif bad == 'empty_instruction': task['instruction'] = '  '
    elif bad == 'long_instruction': task['instruction'] = '字' * 1201
    elif bad == 'control_instruction': task['instruction'] += '\x00'
    elif bad == 'empty_sections': task['sections'] = []
    elif bad == 'many_sections': task['sections'] *= 2
    elif bad == 'duplicate_sections': task['sections'][1]['id'] = section['id']
    elif bad == 'section_extra': section['extra'] = True
    elif bad == 'question_mode': section['mode'] = 'QUESTION'
    elif bad == 'empty_section_instruction': section['instruction'] = '\n\t'
    elif bad == 'long_section_instruction': section['instruction'] = '字' * 601
    elif bad == 'empty_basis': section['basis'] = []
    elif bad == 'many_basis': section['basis'] *= 4
    elif bad == 'duplicate_basis': section['basis'] *= 2
    elif bad == 'foreign_source': ref['id'] = 'hidden-material'
    elif bad == 'discussion_source': ref.update(collection='discussion', id='question', passage_ids=['p0001'])
    elif bad == 'unknown_passage': ref['passage_ids'] = ['p9999']
    elif bad == 'duplicate_passage': ref['passage_ids'] *= 2
    elif bad == 'empty_passages': ref['passage_ids'] = []
    elif bad == 'many_passages': ref['passage_ids'] = [f'p{n:04d}' for n in range(1, 8)]
    elif bad == 'basis_extra': ref['text'] = '附加伪造正文。'
    with pytest.raises(ValueError): validate_topic_plan(task, sources(c))


def test_projection_retains_original_passage_ids_and_text_without_mutating_source():
    c = context(); wire = passage_wire_context(c); old_c = deepcopy(c); old_wire = deepcopy(wire)
    projected = project_topic_wire(wire, c)
    assert c == old_c and wire == old_wire
    assert [(m['collection'], m['id']) for m in projected['materials']] == [('knowledge', 'own'), ('evidence', 'notice')]
    assert projected['materials'][0]['passages'] == [{'id': 'p0002', 'text': '不知何时，又醒过一次。'}]
    assert projected['materials'][1]['passages'] == wire['materials'][1]['passages']
    assert projected['strategy_materials'] == []
    assert projected['discussion'] == [wire['discussion'][1]]
    assert projected['history_window']['omitted_count'] == 8
    assert project_topic_wire(projected, c) == projected


def test_selected_passages_are_unioned_in_original_order_across_sections():
    c = context()
    c['topic_response_task']['sections'][1]['basis'] = [basis(passages=['p0003', 'p0001'])]
    projected = project_topic_wire(passage_wire_context(c), c)
    assert len(projected['materials']) == 1
    assert [p['id'] for p in projected['materials'][0]['passages']] == ['p0001', 'p0002', 'p0003']


def test_context_without_task_preserves_old_wire_and_does_not_check_new_output_contract():
    c = context(); c.pop('topic_response_task'); wire = passage_wire_context(c)
    assert project_topic_wire(wire, c) == wire
    validate_topic_plan_output({'segments': []}, c)


@pytest.mark.parametrize('bad', ['missing_material', 'duplicate_material', 'missing_passage', 'changed_passage', 'duplicate_passage', 'missing_target'])
def test_projection_rejects_divergent_source_or_target(bad):
    c = context(); wire = passage_wire_context(c)
    if bad == 'missing_material': wire['materials'].pop(0)
    elif bad == 'duplicate_material': wire['materials'].append(deepcopy(wire['materials'][0]))
    elif bad == 'missing_passage': wire['materials'][0]['passages'].pop(1)
    elif bad == 'changed_passage': wire['materials'][0]['passages'][1]['text'] += '六点。'
    elif bad == 'duplicate_passage': wire['materials'][0]['passages'].append(deepcopy(wire['materials'][0]['passages'][1]))
    elif bad == 'missing_target': wire['discussion'].pop(1)
    with pytest.raises(ValueError): project_topic_wire(wire, c)


def test_complete_output_and_unknown_pass_without_rewriting_original():
    c = context(); value = speech(); before = deepcopy(value)
    validate_topic_plan_output(value, c)
    assert value == before
    validate_topic_plan_output({'segments': [{'mode': 'UNCERTAIN', 'text': '', 'basis': []}]}, c)


@pytest.mark.parametrize('bad', ['missing_segment', 'extra_segment', 'wrong_order', 'wrong_mode',
    'missing_basis', 'extra_basis', 'wrong_collection', 'wrong_id', 'wrong_passage',
    'missing_passage', 'extra_passage', 'duplicate_basis', 'duplicate_passage'])
def test_incomplete_or_misbound_output_is_rejected_without_repair(bad):
    c = context(); value = speech(); segment = value['segments'][0]; ref = segment['basis'][0]
    if bad == 'missing_segment': value['segments'].pop()
    elif bad == 'extra_segment': value['segments'].append(deepcopy(segment))
    elif bad == 'wrong_order': value['segments'].reverse()
    elif bad == 'wrong_mode': segment['mode'] = 'INFERENCE'
    elif bad == 'missing_basis': segment['basis'] = []
    elif bad == 'extra_basis': segment['basis'].append(basis('notice', ['p0001'], 'evidence'))
    elif bad == 'wrong_collection': ref['collection'] = 'memory'
    elif bad == 'wrong_id': ref['id'] = 'other'
    elif bad == 'wrong_passage': ref['passage_ids'] = ['p0001']
    elif bad == 'missing_passage': ref['passage_ids'] = []
    elif bad == 'extra_passage': ref['passage_ids'].append('p0001')
    elif bad == 'duplicate_basis': segment['basis'].append(deepcopy(ref))
    elif bad == 'duplicate_passage': ref['passage_ids'] *= 2
    before = deepcopy(value)
    with pytest.raises(ValueError): validate_topic_plan_output(value, c)
    assert value == before


def test_output_basis_and_passage_order_do_not_change_set_identity():
    c = context(); task = c['topic_response_task']
    task['sections'][0]['basis'] = [basis(passages=['p0001', 'p0002']), basis('notice', ['p0001'], 'evidence')]
    value = {'segments': [{'mode': s['mode'], 'text': '相关表达。', 'basis': deepcopy(s['basis'])}
                          for s in task['sections']]}
    value['segments'][0]['basis'].reverse()
    value['segments'][0]['basis'][1]['passage_ids'].reverse()
    validate_topic_plan_output(value, c)

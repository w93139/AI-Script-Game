"""Synthetic table 1.3 contract; no real sources, calls, truth injection or scores.

Scope: lossless passage wire, finite private assessment, replay projection,
legacy snapshots and exact provider wire budgets. Integration binds new games
separately; this adapter never upgrades a game or supplies missing answers.
"""
import asyncio
from copy import deepcopy
import json
from unittest.mock import AsyncMock

from jsonschema import Draft202012Validator
import pytest

from src.fusion.package_role_model import PackageRoleModelError
from src.fusion.package_table_model import (
    EVIDENCE_MODEL_CONTRACT, EvidencePackageTableModel, PackageTableModel,
    BoundPackageTableModel, ReasonedPackageTableModel, output_schema,
    table_context_window, validate_evidence_decision,
)
from src.fusion.table_evidence import (
    ASSESSMENT_VERSION, EVIDENCE_POLICY, PASSAGE_POLICY, evidence_passage_index,
    evidence_projection, evidence_wire_context,
)
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_bound_table_model import context, settings, response


def assessment(c=None):
    c = c or context()
    return {'schema_version': ASSESSMENT_VERSION,
        'answers': [dict(question_id=q['id'], selections=[dict(option_id=q['options'][0]['id'],
                         certainty='DIRECT', basis=['m0001.p0001'], summary='依据当前片段选择。')]
                         if q['options'] else []) for q in c['questions']],
        'vote': {'accusation_id': 'b', 'trust_character_id': 'a'},
        'reflection': {'text': '', 'certainty': 'UNKNOWN', 'basis': []}}


@pytest.mark.parametrize('text', [
    '  早晨见到蓝色盒子。\n\n  晚间只听见一声铃响。 \n',
    '\t(07:03) 甲的说法。\r\n（??：??）乙的说法。\n',
    '字' * 641 + '\n\n' + '另一段。' * 160 + ' \t',
    ' \n\t',
])
def test_passages_preserve_every_character_source_attribute_and_order(text):
    c = context(); c['materials'][0]['text'] = text; c['discussion'][0]['text'] = text
    original = deepcopy(c); wire = evidence_wire_context(c); index = evidence_passage_index(c)
    for field, prefix in (('materials', 'm'), ('discussion', 'd')):
        before, after = c[field][0], wire[field][0]
        assert 'text' not in after
        assert ''.join(p['text'] for p in after['passages']) == text
        assert {k: v for k, v in after.items() if k != 'passages'} == {k: v for k, v in before.items() if k != 'text'}
        for p in after['passages']:
            assert p['id'].startswith(prefix + '0001.p')
            assert index[p['id']]['text'] == p['text'] and index[p['id']]['id'] == before['id']
    assert index['m0001.p0001']['public'] is False
    assert index['d0001.p0001']['speaker'] == 'a' and index['d0001.p0001']['sequence'] == 1
    assert c == original and wire['schema_version'] == c['schema_version']


def test_prepare_freezes_original_context_but_sends_only_lossless_passages():
    c = context(); c['materials'][0]['text'] = '  第一条明确经历。\n\n第二条带时间限定。\n'
    model = EvidencePackageTableModel(object(), settings()); frozen = model.prepare(c)
    wire = json.loads(frozen['messages'][1]['content'])['context']
    assert wire['schema_version'] == 'package-table-context/1.1'
    assert wire['passage_policy'] == PASSAGE_POLICY
    assert frozen['source_context'] == c and frozen['context_hash'] == content_hash(c)
    assert frozen['wire_context_hash'] == content_hash(wire)
    assert model._prepared_payload(frozen)['context'] == c
    assert wire['questions'] == c['questions'] and wire['character'] == c['character']
    assert 'text' not in wire['materials'][0] and 'text' not in wire['discussion'][0]
    assert 'trigger' not in canonical_json(wire)
    assert model.metadata()['evidence_policy'] == EVIDENCE_POLICY
    assert model.metadata()['schema_version'] == EVIDENCE_MODEL_CONTRACT
    assert '引用存在不代表已证明结论' in frozen['messages'][0]['content']


@pytest.mark.parametrize('certainty', ['DIRECT', 'INFERRED', 'UNKNOWN'])
def test_short_assessment_projects_only_existing_submission_and_keeps_vote_independent(certainty):
    c = context(); value = assessment(c)
    item = value['answers'][0]
    if certainty == 'UNKNOWN': item['selections'] = []
    else: item['selections'][0].update(certainty=certainty, basis=['d0001.p0001'])
    if certainty != 'UNKNOWN':
        value['reflection'] = {'text': '盒子可能值得再核对。', 'certainty': certainty, 'basis': ['m0001.p0001']}
    before = deepcopy(value)
    model = EvidencePackageTableModel(object(), settings())
    result = model._read_output(canonical_json(value), model.prepare(c))
    assert result['assessment'] == value and value == before
    decision = result['decision']
    assert set(decision) == {'schema_version', 'answers', 'vote', 'reflection'}
    assert all(set(a) == {'question_id', 'option_ids'} for a in decision['answers'])
    assert decision['vote'] == value['vote']  # Self-accusation is a legal strategy.
    assert decision['answers'][0]['option_ids'] == [s['option_id'] for s in item['selections']]
    assert decision['reflection'] == ('推测：' if certainty == 'INFERRED' else '') + value['reflection']['text']
    assert validate_evidence_decision(decision, value, c) == value
    Draft202012Validator(output_schema(c, EVIDENCE_MODEL_CONTRACT)).validate(value)


@pytest.mark.parametrize('kind', [
    'missing_question', 'duplicate_question', 'foreign_question', 'foreign_option', 'too_many',
    'duplicate_option', 'unknown_selected', 'unknown_summary', 'unknown_basis', 'direct_empty',
    'missing_basis', 'blank_summary', 'foreign_passage', 'wrong_source_prefix', 'duplicate_basis',
    'too_many_basis', 'reflection_unreferenced', 'reflection_unknown_text', 'reflection_foreign',
    'bad_vote', 'extra_field', 'long_summary',
])
def test_inconsistent_or_untraceable_assessment_is_rejected_without_repair(kind):
    c = context(); value = assessment(c); first = value['answers'][0]; selected = first['selections'][0]
    if kind == 'missing_question': value['answers'].pop()
    elif kind == 'duplicate_question': value['answers'][2] = deepcopy(first)
    elif kind == 'foreign_question': first['question_id'] = 'future-question'
    elif kind == 'foreign_option': selected['option_id'] = 'north'
    elif kind == 'too_many': first['selections'].append({**deepcopy(selected), 'option_id': 'blue'})
    elif kind == 'duplicate_option': value['answers'][1]['selections'] *= 2
    elif kind == 'unknown_selected': selected['certainty'] = 'UNKNOWN'
    elif kind == 'unknown_summary': value['answers'][2]['summary'] = '已经确定某个选项。'
    elif kind == 'unknown_basis': value['answers'][2]['basis'] = ['m0001.p0001']
    elif kind == 'direct_empty': selected['option_id'] = ''
    elif kind == 'missing_basis': selected['basis'] = []
    elif kind == 'blank_summary': selected['summary'] = '  '
    elif kind == 'foreign_passage': selected['basis'] = ['m0001.p9999']
    elif kind == 'wrong_source_prefix': selected['basis'] = ['m9999.p0001']
    elif kind == 'duplicate_basis': selected['basis'] *= 2
    elif kind == 'too_many_basis': selected['basis'] *= 4
    elif kind == 'reflection_unreferenced': value['reflection'] = {'text': '某个结论。', 'certainty': 'DIRECT', 'basis': []}
    elif kind == 'reflection_unknown_text': value['reflection']['text'] = '凭空出现的结论。'
    elif kind == 'reflection_foreign': value['reflection'] = {'text': '有待核对。', 'certainty': 'INFERRED', 'basis': ['d0002.p0001']}
    elif kind == 'bad_vote': value['vote']['trust_character_id'] = 'b'
    elif kind == 'extra_field': selected['score'] = 100
    elif kind == 'long_summary': selected['summary'] = '字' * 49
    before = deepcopy(value)
    model = EvidencePackageTableModel(object(), settings())
    with pytest.raises(ValueError): model._read_output(canonical_json(value), model.prepare(c))
    assert value == before


@pytest.mark.parametrize('field', ['answers', 'vote', 'reflection'])
def test_replay_rejects_decision_that_disagrees_with_private_assessment(field):
    c = context(); value = assessment(c); decision, _ = evidence_projection(value, c)
    if field == 'answers': decision['answers'][0]['option_ids'] = ['blue']
    elif field == 'vote': decision['vote']['accusation_id'] = None
    else: decision['reflection'] = '新添一句。'
    with pytest.raises(ValueError, match='TABLE_EVIDENCE_DECISION_MISMATCH'):
        validate_evidence_decision(decision, value, c)


def test_dynamic_schema_binds_question_options_certainty_and_visible_passages():
    c = context(); schema = output_schema(c, EVIDENCE_MODEL_CONTRACT)
    Draft202012Validator.check_schema(schema); validator = Draft202012Validator(schema)
    original = assessment(c); assert validator.is_valid(original)
    mutations = [
        ('option_id', 'north'), ('certainty', 'UNKNOWN'),
        ('basis', []), ('basis', ['m0001.p9999']), ('summary', ''),
    ]
    for key, value in mutations:
        bad = deepcopy(original); bad['answers'][0]['selections'][0][key] = value
        assert not validator.is_valid(bad)
    c['materials'] = []; c['discussion'] = []
    empty = assessment(c)
    for item in empty['answers']: item['selections'] = []
    schema = output_schema(c, EVIDENCE_MODEL_CONTRACT)
    Draft202012Validator.check_schema(schema); Draft202012Validator(schema).validate(empty)
    model = EvidencePackageTableModel(object(), settings())
    result = model._read_output(canonical_json(empty), model.prepare(c))
    assert all(not item['option_ids'] for item in result['decision']['answers'])


@pytest.mark.parametrize('count', [0, 2, 5])
def test_five_independent_options_each_keep_their_own_sources_and_certainty(count):
    c = context()
    c['materials'] = [dict(collection='evidence', id=f'record-{n}', kind='FACT', public=True,
                           text=f'合成记录{n}记载对应的物件。') for n in range(1, 6)]
    c['questions'][0].update(max_choices=5, options=[dict(id=f'option-{n}', label=f'合成物件{n}') for n in range(1, 6)])
    value = assessment(c)
    value['answers'][0]['selections'] = [dict(option_id=f'option-{n}',
        certainty='DIRECT' if n % 2 else 'INFERRED', basis=[f'm{n:04d}.p0001'],
        summary=f'记录{n}直接记载。' if n % 2 else f'按记录{n}作有限推测。') for n in range(1, count + 1)]
    model = EvidencePackageTableModel(object(), settings()); prepared = model.prepare(c)
    Draft202012Validator(prepared['params']['response_format']['json_schema']['schema']).validate(value)
    result = model._read_output(canonical_json(value), prepared)
    assert result['assessment'] == value
    assert result['decision']['answers'][0]['option_ids'] == [f'option-{n}' for n in range(1, count + 1)]
    assert set(result['assessment']['answers'][0]) == {'question_id', 'selections'}
    assert len({ref for selection in value['answers'][0]['selections'] for ref in selection['basis']}) == count
    if count > 1:
        assert {selection['certainty'] for selection in value['answers'][0]['selections']} == {'DIRECT', 'INFERRED'}
        for mutation in ('duplicate_option', 'missing_basis', 'foreign_option'):
            bad = deepcopy(value); selected = bad['answers'][0]['selections'][-1]
            if mutation == 'duplicate_option': selected['option_id'] = 'option-1'
            elif mutation == 'missing_basis': selected['basis'] = []
            else: selected['option_id'] = 'north'
            with pytest.raises(ValueError): model._read_output(canonical_json(bad), prepared)


def test_reference_existence_is_not_an_entailment_or_correct_answer_oracle():
    # Deliberately unrelated text with an existing reference demonstrates the
    # boundary: structural acceptance is not a semantic review certificate.
    c = context(); c['materials'][0]['text'] = '这里仅记载天气晴朗。'
    value = assessment(c); model = EvidencePackageTableModel(object(), settings())
    result = model._read_output(canonical_json(value), model.prepare(c))
    assert result['assessment']['answers'][0]['selections'][0]['certainty'] == 'DIRECT'
    assert 'verified' not in canonical_json(result) and 'score' not in canonical_json(result)


@pytest.mark.parametrize('action', ['CAST_BALLOT', 'BREAK_TIE'])
def test_nonfinale_wire_and_decision_keep_table_12_behavior(action):
    c = context(); c.update(action=action, options=[{'id': 'go', 'label': '合成地点', 'cost': 1}],
                            questions=[], accusation_options=[], trust_character_ids=[])
    old = ReasonedPackageTableModel(object(), settings()); new = EvidencePackageTableModel(object(), settings())
    assert old.prepare(c) == new.prepare(c)
    value = {'choice_id': 'go', **({'kind': 'CHOOSE'} if action == 'CAST_BALLOT' else {})}
    assert new._read_output(canonical_json(value), new.prepare(c)) == {'decision': value}
    with pytest.raises(ValueError): validate_evidence_decision(value, assessment(), c)


@pytest.mark.parametrize('kind', ['source', 'wire', 'schema', 'wire_hash', 'reservation'])
def test_prepared_tampering_is_rejected_before_sdk(kind):
    sdk = AsyncMock(); model = EvidencePackageTableModel(sdk, settings())
    prepared = model.prepare(context()); bad = deepcopy(prepared)
    if kind == 'source': bad['source_context']['materials'][0]['text'] += '新增事实。'
    elif kind == 'wire':
        payload = json.loads(bad['messages'][1]['content']); payload['context']['materials'][0]['passages'][0]['text'] += '篡改。'
        bad['messages'][1]['content'] = canonical_json(payload)
    elif kind == 'schema': bad['params']['response_format']['json_schema']['schema']['$defs']['EvidenceBasis']['maxItems'] = 9
    elif kind == 'wire_hash': bad['wire_context_hash'] = '0' * 64
    else: bad['output_tokens'] += 1
    result = asyncio.run(model.call(bad))
    assert result['model_attempted'] is False and result['status'] == 'INVALID'
    sdk.chat_completion.assert_not_awaited(); assert model.prepare(context()) == prepared


def test_mock_dispatch_returns_private_assessment_and_replayable_original_decision_once():
    sdk = AsyncMock(); model = EvidencePackageTableModel(sdk, settings()); frozen = model.prepare(context())
    value = assessment()
    async def complete(messages, **params):
        assert [dict(role=m.role, content=m.content) for m in messages] == frozen['messages']
        assert params == frozen['params']; return response(value)
    sdk.chat_completion.side_effect = complete
    result = asyncio.run(model.call(frozen))
    assert result['status'] == 'OK' and result['assessment'] == value
    assert validate_evidence_decision(result['decision'], result['assessment'], context()) == value
    assert sdk.chat_completion.await_count == 1


@pytest.mark.parametrize('provider', ['ark', 'ant'])
def test_28_question_exact_wire_budget_includes_passages_dynamic_schema_and_ant_restatement(provider):
    c = context(); c['questions'] = [dict(id=f'q-{n}', prompt=f'合成题{n}', max_choices=1,
        options=[dict(id=f'choice-{n}-{i}', label=f'选项{i}') for i in range(4)]) for n in range(28)]
    c['discussion'] = [dict(id=f'claim-{n}', sequence=n, speaker='a', kind='CLAIM', text='合成发言。' * 40) for n in range(1, 61)]
    cfg = settings(max_input_bytes=98304, **({'provider': 'ant_digital', 'model': 'qwen3.6-plus'} if provider == 'ant' else {}))
    model = EvidencePackageTableModel(object(), cfg); original = deepcopy(c)
    window = table_context_window(c, 98304, EVIDENCE_MODEL_CONTRACT, model.metadata())
    full = model.prepare(window); size = full['input_tokens'] - 4096
    assert size == len(canonical_json(full['messages']).encode()) + len(canonical_json(full['params']['response_format']).encode())
    shorter = table_context_window(c, size - 1, EVIDENCE_MODEL_CONTRACT, model.metadata())
    assert len(shorter['discussion']) < len(window['discussion'])
    assert model.prepare(shorter)['input_tokens'] - 4096 <= size - 1
    assert shorter['materials'] == c['materials'] and shorter['questions'] == c['questions'] and c == original
    assert full['params']['max_tokens'] == 4096 and full['output_tokens'] >= 4096
    value = assessment(window)
    Draft202012Validator(full['params']['response_format']['json_schema']['schema']).validate(value)
    assert len(model._read_output(canonical_json(value), full)['decision']['answers']) == 28
    c['discussion'] = []
    minimum = model.prepare(table_context_window(c, 98304, EVIDENCE_MODEL_CONTRACT, model.metadata()))['input_tokens'] - 4096
    with pytest.raises(PackageRoleModelError, match='FULL_PLAY_REQUIRED_CONTEXT_TOO_LARGE'):
        table_context_window(c, minimum - 1, EVIDENCE_MODEL_CONTRACT, model.metadata())


@pytest.mark.parametrize('cls,metadata_hash,prepared_hash', [
    (PackageTableModel, 'e11f7438858e24dfff9948d4cd92ad4d7ac889529180d82affd6bb38e77a5e60', '24753cf3f00172752d6d92eb07daf099080bd9e63ff9c8cb903ce6d4b441fb5d'),
    (BoundPackageTableModel, '43dc09b53b7fc59e638ba0c396851769bf1f07eabcde0b156d256f08a94e2513', '314f1a84604801aa654deb215bb46cd9dcfe4a6bcca20fa3d0dc89bf1f682834'),
    (ReasonedPackageTableModel, '145c64e5333f7dd95195e0ae81fa639af1b81dc586cd824e3b7785591d4ff2c6', '5c115463b38652616df2838e2984b7b9b9e9a165a77fc9e475a2197ec5ae065f'),
])
def test_every_pre_evidence_version_retains_exact_metadata_and_wire(cls, metadata_hash, prepared_hash):
    model = cls(object(), settings())
    assert content_hash(model.metadata()) == metadata_hash
    assert content_hash(model.prepare(context())) == prepared_hash


def test_new_evidence_metadata_dynamic_schema_and_both_context_hashes_are_pinned():
    model = EvidencePackageTableModel(object(), settings()); prepared = model.prepare(context())
    assert content_hash(model.metadata()) == '70d463a85febfbee100296c8927012340f2032beef9f8426ba50dee2880a6cd3'
    assert content_hash(output_schema(context(), EVIDENCE_MODEL_CONTRACT)) == 'c5ae4dc4a7f088a3bf14eb26c8e883df63dd1289d7579e5f302e7cc1227c5f32'
    assert prepared['context_hash'] == 'cf91303851952a50dd2de31f00549d1d92182c7cfca770aaf0b532340536bb4a'
    assert prepared['wire_context_hash'] == '104e14ae4b11cf0018018718899b208a87d0416befaa63ac2da52c240d28ded0'
    assert content_hash(prepared) == 'd31f569f99bb25799fbcbfe71443cdf327269b9cd4fcd9944cca010daae853c2'

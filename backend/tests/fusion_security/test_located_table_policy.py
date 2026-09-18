"""Synthetic table 1.4: authorized locations and source-addressed evidence only.

The adapter never derives locations, hidden facts, answers or missing memories.
Old policies, source text, finite questions, votes and recovery remain frozen.
"""
import asyncio
from copy import deepcopy
import json
from unittest.mock import AsyncMock

from jsonschema import Draft202012Validator
import pytest

from src.fusion.package_role_model import PackageRoleModelError
from src.fusion.package_table_model import (
    EVIDENCE_MODEL_CONTRACT, LOCATED_MODEL_CONTRACT, EvidencePackageTableModel,
    LocatedPackageTableModel, LocatedTableContext, output_schema,
    table_context_window, validate_evidence_decision,
)
from src.fusion.located_evidence import SOURCE_POLICY, source_passage_index
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_bound_table_model import context, response, settings
from tests.fusion_security.test_evidence_table_policy import assessment as old_assessment


def located_context():
    c = context()
    c.update(schema_version='package-table-context/1.2', evidence_origins=[
        {'id': 'card-counter', 'labels': ['西侧储物间', '计数器调查']}])
    c['materials'].append({'collection': 'evidence', 'id': 'card-counter',
        'text': '花费一次调查查看计数器。\n\n计数器只显示一次记录。 \n',
        'kind': 'FACT', 'public': True})
    return c


def assessment(c=None):
    c = c or located_context()
    value = old_assessment(c)
    value['schema_version'] = 'table-evidence-assessment/1.1'
    for answer in value['answers']:
        for selection in answer['selections']:
            selection['basis'] = ['e:card-counter/p1']
    return value


def test_located_prepare_keeps_every_source_and_location_without_duplicate_text():
    c = located_context(); original = deepcopy(c)
    model = LocatedPackageTableModel(object(), settings()); frozen = model.prepare(c)
    wire = json.loads(frozen['messages'][1]['content'])['context']
    assert wire['schema_version'] == 'package-table-context/1.3'
    assert wire['passage_policy'] == SOURCE_POLICY
    assert wire['evidence_origins'] == c['evidence_origins']
    assert frozen['source_context'] == c and frozen['context_hash'] == content_hash(c)
    assert frozen['wire_context_hash'] == content_hash(wire)
    assert model._prepared_payload(frozen)['context'] == c
    assert wire['questions'] == c['questions'] and wire['character'] == c['character']
    for field in ('materials', 'discussion'):
        for before, after in zip(c[field], wire[field], strict=True):
            assert 'text' not in after
            assert ''.join(p['text'] for p in after['passages']) == before['text']
            assert {k: v for k, v in after.items() if k != 'passages'} == {k: v for k, v in before.items() if k != 'text'}
    assert wire['materials'][-1]['passages'] == [{'id': 'e:card-counter/p1', 'text': c['materials'][-1]['text']}]
    assert c == original
    metadata = model.metadata()
    assert metadata['schema_version'] == LOCATED_MODEL_CONTRACT
    assert metadata['source_context_contract'] == c['schema_version']
    assert metadata['finale_context_contract'] == wire['schema_version']
    assert metadata['passage_policy'] == SOURCE_POLICY
    prompt = frozen['messages'][0]['content']
    assert 'table-evidence-assessment/1.1' in prompt and 'mNNNN' not in prompt
    assert '不能借用另一物证的标签' in prompt


@pytest.mark.parametrize('bad', [
    'missing_origins', 'foreign_id', 'knowledge_id', 'duplicate_id', 'duplicate_label',
    'blank_label', 'bad_label_type', 'extra_origin_field', 'old_schema', 'wire_schema',
    'nonfinale', 'material_removed',
])
def test_invalid_or_ungranted_location_context_rejected_before_dispatch(bad):
    c = located_context(); origin = c['evidence_origins'][0]
    if bad == 'missing_origins': c.pop('evidence_origins')
    elif bad == 'foreign_id': origin['id'] = 'hidden-card'
    elif bad == 'knowledge_id': origin['id'] = c['materials'][0]['id']
    elif bad == 'duplicate_id': c['evidence_origins'].append(deepcopy(origin))
    elif bad == 'duplicate_label': origin['labels'] *= 2
    elif bad == 'blank_label': origin['labels'] = [' \t']
    elif bad == 'bad_label_type': origin['labels'] = [1]
    elif bad == 'extra_origin_field': origin['answer'] = 'red'
    elif bad == 'old_schema': c['schema_version'] = 'package-table-context/1.0'
    elif bad == 'wire_schema': c['schema_version'] = 'package-table-context/1.3'
    elif bad == 'nonfinale': c.update(action='CAST_BALLOT', options=[dict(id='go', label='院子', cost=1)],
                                    questions=[], accusation_options=[], trust_character_ids=[])
    else: c['materials'].pop()
    sdk = AsyncMock(); model = LocatedPackageTableModel(sdk, settings())
    with pytest.raises(PackageRoleModelError, match='PACKAGE_TABLE_INPUT_INVALID'):
        model.prepare(c)
    sdk.chat_completion.assert_not_awaited()


@pytest.mark.parametrize('origins', [[], [{'id': 'card-counter', 'labels': []}]])
def test_absent_location_does_not_invent_mapping_or_repair_unknown_answers(origins):
    c = located_context(); c['evidence_origins'] = origins
    value = assessment(c)
    for answer in value['answers']: answer['selections'] = []
    model = LocatedPackageTableModel(object(), settings()); frozen = model.prepare(c)
    result = model._read_output(canonical_json(value), frozen)
    assert all(not a['option_ids'] for a in result['decision']['answers'])
    assert result['assessment'] == value
    assert json.loads(frozen['messages'][1]['content'])['context']['evidence_origins'] == origins
    assert validate_evidence_decision(result['decision'], value, c) == value


def test_source_addressed_schema_and_replay_preserve_decision_shape_and_vote_independence():
    c = located_context(); value = assessment(c)
    value['answers'][0]['selections'][0]['certainty'] = 'INFERRED'
    model = LocatedPackageTableModel(object(), settings()); frozen = model.prepare(c)
    result = model._read_output(canonical_json(value), frozen)
    assert result['assessment'] == value
    assert result['decision']['vote'] == value['vote']
    assert all(set(a) == {'question_id', 'option_ids'} for a in result['decision']['answers'])
    assert set(result['decision']) == {'schema_version', 'answers', 'vote', 'reflection'}
    assert validate_evidence_decision(result['decision'], value, c) == value
    Draft202012Validator(output_schema(c, LOCATED_MODEL_CONTRACT)).validate(value)
    for basis in ('e:unseen-card/p1', 'k:card-counter/p1', 'm0002.p0001', 'e:card-counter/p2'):
        bad = deepcopy(value); bad['answers'][0]['selections'][0]['basis'] = [basis]
        assert not Draft202012Validator(output_schema(c, LOCATED_MODEL_CONTRACT)).is_valid(bad)
        with pytest.raises(ValueError): model._read_output(canonical_json(bad), frozen)
    bad_context = deepcopy(c); bad_context['evidence_origins'][0]['id'] = 'ungranted'
    with pytest.raises(ValueError): validate_evidence_decision(result['decision'], value, bad_context)
    bad_decision = deepcopy(result['decision']); bad_decision['answers'][0]['option_ids'] = []
    with pytest.raises(ValueError, match='TABLE_EVIDENCE_DECISION_MISMATCH'):
        validate_evidence_decision(bad_decision, value, c)


def test_old_and_new_contexts_assessments_and_prepared_requests_do_not_cross_versions():
    old = EvidencePackageTableModel(object(), settings()); new = LocatedPackageTableModel(object(), settings())
    old_context = context(); new_context = located_context()
    with pytest.raises(PackageRoleModelError): old.prepare(new_context)
    with pytest.raises(PackageRoleModelError): new.prepare(old_context)
    with pytest.raises(ValueError): new._read_output(canonical_json(old_assessment()), new.prepare(new_context))
    with pytest.raises(ValueError): old._read_output(canonical_json(assessment()), old.prepare(old_context))
    old_result = old._read_output(canonical_json(old_assessment()), old.prepare(old_context))
    assert validate_evidence_decision(old_result['decision'], old_result['assessment'], old_context) == old_assessment()
    assert asyncio.run(new.call(old.prepare(old_context)))['model_attempted'] is False
    assert asyncio.run(old.call(new.prepare(new_context)))['model_attempted'] is False


@pytest.mark.parametrize('action', ['CAST_BALLOT', 'BREAK_TIE'])
def test_new_policy_nonfinale_remains_byte_identical_to_table_13(action):
    c = context(); c.update(action=action, options=[dict(id='go', label='院子', cost=1)],
                            questions=[], accusation_options=[], trust_character_ids=[])
    old = EvidencePackageTableModel(object(), settings()); new = LocatedPackageTableModel(object(), settings())
    assert old.prepare(c) == new.prepare(c)
    value = {'choice_id': 'go', **({'kind': 'CHOOSE'} if action == 'CAST_BALLOT' else {})}
    assert new._read_output(canonical_json(value), new.prepare(c)) == {'decision': value}


@pytest.mark.parametrize('kind', ['source_origin', 'wire_origin', 'source_id', 'schema_version', 'wire_hash'])
def test_location_or_reference_tampering_fails_before_sdk(kind):
    sdk = AsyncMock(); model = LocatedPackageTableModel(sdk, settings())
    original = model.prepare(located_context()); bad = deepcopy(original)
    if kind == 'source_origin': bad['source_context']['evidence_origins'][0]['labels'] = ['另一个房间']
    elif kind == 'wire_origin':
        payload = json.loads(bad['messages'][1]['content']); payload['context']['evidence_origins'][0]['labels'] = ['另一个房间']
        bad['messages'][1]['content'] = canonical_json(payload)
    elif kind == 'source_id': bad['source_context']['materials'][-1]['id'] = 'other'
    elif kind == 'schema_version': bad['source_context']['schema_version'] = 'package-table-context/1.0'
    else: bad['wire_context_hash'] = '0' * 64
    result = asyncio.run(model.call(bad))
    assert result['status'] == 'INVALID' and result['model_attempted'] is False
    sdk.chat_completion.assert_not_awaited()


def test_mock_call_once_reconstructs_exact_source_addressed_wire_and_replays():
    sdk = AsyncMock(); model = LocatedPackageTableModel(sdk, settings())
    c = located_context(); frozen = model.prepare(c); value = assessment(c)
    async def complete(messages, **params):
        assert [dict(role=m.role, content=m.content) for m in messages] == frozen['messages']
        assert params == frozen['params']
        return response(value)
    sdk.chat_completion.side_effect = complete
    result = asyncio.run(model.call(frozen))
    assert result['status'] == 'OK' and result['assessment'] == value
    assert validate_evidence_decision(result['decision'], value, c) == value
    assert sdk.chat_completion.await_count == 1


@pytest.mark.parametrize('provider', ['ark', 'ant'])
def test_28_question_wire_accounts_for_origins_ids_schema_and_ant_restatement(provider):
    c = located_context(); c['questions'] = [dict(id=f'q-{n}', prompt=f'合成题{n}', max_choices=1,
        options=[dict(id=f'choice-{n}-{i}', label=f'选项{i}') for i in range(4)]) for n in range(28)]
    c['discussion'] = [dict(id=f'claim-{n}', sequence=n, speaker='a', kind='CLAIM', text='合成发言。' * 40) for n in range(1, 61)]
    cfg = settings(max_input_bytes=98304, **({'provider': 'ant_digital', 'model': 'qwen3.6-plus'} if provider == 'ant' else {}))
    model = LocatedPackageTableModel(object(), cfg); original = deepcopy(c)
    window = table_context_window(c, 98304, LOCATED_MODEL_CONTRACT, model.metadata())
    frozen = model.prepare(window); size = frozen['input_tokens'] - 4096
    assert size == len(canonical_json(frozen['messages']).encode()) + len(canonical_json(frozen['params']['response_format']).encode())
    shorter = table_context_window(c, size - 1, LOCATED_MODEL_CONTRACT, model.metadata())
    assert len(shorter['discussion']) < len(window['discussion'])
    assert model.prepare(shorter)['input_tokens'] - 4096 <= size - 1
    assert shorter['materials'] == c['materials'] and shorter['questions'] == c['questions']
    assert shorter['evidence_origins'] == c['evidence_origins'] and c == original
    assert frozen['params']['max_tokens'] == 4096 and model.input_byte_ceiling == 98304
    value = assessment(window)
    Draft202012Validator(frozen['params']['response_format']['json_schema']['schema']).validate(value)
    assert len(model._read_output(canonical_json(value), frozen)['decision']['answers']) == 28
    for item in shorter['discussion']:
        assert f'd:{item["id"]}/p1' in source_passage_index(shorter)
    c['discussion'] = []
    minimum = model.prepare(table_context_window(c, 98304, LOCATED_MODEL_CONTRACT, model.metadata()))['input_tokens'] - 4096
    with pytest.raises(PackageRoleModelError, match='FULL_PLAY_REQUIRED_CONTEXT_TOO_LARGE'):
        table_context_window(c, minimum - 1, LOCATED_MODEL_CONTRACT, model.metadata())


def test_location_contract_is_strict_while_table_13_frozen_snapshot_stays_identical():
    assert LocatedTableContext.model_validate(located_context()).model_dump() == located_context()
    old = EvidencePackageTableModel(object(), settings())
    assert content_hash(old.metadata()) == '70d463a85febfbee100296c8927012340f2032beef9f8426ba50dee2880a6cd3'
    assert content_hash(old.prepare(context())) == 'd31f569f99bb25799fbcbfe71443cdf327269b9cd4fcd9944cca010daae853c2'
    assert content_hash(output_schema(context(), EVIDENCE_MODEL_CONTRACT)) == 'c5ae4dc4a7f088a3bf14eb26c8e883df63dd1289d7579e5f302e7cc1227c5f32'


def test_located_metadata_dynamic_schema_source_and_wire_are_pinned():
    c = located_context(); model = LocatedPackageTableModel(object(), settings())
    frozen = model.prepare(c)
    assert content_hash(model.metadata()) == '7ffdf9447915b66afee05fb2bb2a9dee34cf86a068346400972532444d9955c4'
    assert content_hash(output_schema(c, LOCATED_MODEL_CONTRACT)) == '68b60183a2aea0584aaf8d8cdc8d88d963cb4146f802dbea5e6bd9830d8f72d0'
    assert frozen['context_hash'] == 'e06f03ed17b07597b6add70ac32a9fc711a5154d429b6e81edd07762f9463bed'
    assert frozen['wire_context_hash'] == '7b143ac7233fdfa5b9397fce075c9ac98a28e9a20a1f2a212fc704a95f0021b6'
    assert content_hash(frozen) == 'd789ae2eede84e00aa79835afdaeb3021ad820be8228278bd4048126f104e047'

"""Synthetic source-bound question scopes and complete option receipt policy."""
import asyncio
from copy import deepcopy
from hashlib import sha256
import json

from jsonschema import Draft202012Validator
import pytest

from src.fusion.package_role_model import PackageRoleModelError
from src.fusion.package_table_model import (
    SCOPED_MODEL_CONTRACT, ScopedPackageTableModel, LocatedPackageTableModel,
    output_schema, table_context_window, validate_evidence_decision,
)
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_bound_table_model import context, settings
from tests.fusion_security.test_located_table_policy import located_context, assessment as prior_assessment


def scoped_context():
    c = located_context()
    q = c['questions'][0]; source = c['materials'][0]
    c.update(schema_version='package-table-context/1.4', question_scopes=[{
        'question_id': q['id'], 'original_prompt_sha256': sha256(q['prompt'].encode()).hexdigest(),
        'prompt': '在昨天那次经历中，你的第一次选择是什么？',
        'basis': [{'collection': 'knowledge', 'id': source['id'],
                   'text_sha256': sha256(source['text'].encode()).hexdigest()}]}])
    q['options'][0]['label'] = '藏起红盒以避免自己的经历被发现'
    return c


def assessment(c):
    value = prior_assessment(c); value['schema_version'] = 'table-evidence-assessment/1.2'
    options = {q['id']: {o['id']: o['label'] for o in q['options']} for q in c['questions']}
    for a in value['answers']:
        for selection in a['selections']:
            selection['option_text'] = options[a['question_id']][selection['option_id']]
    return value


def test_scoped_wire_keeps_originals_sources_options_and_frozen_context():
    c = scoped_context(); before = deepcopy(c)
    model = ScopedPackageTableModel(object(), settings()); prepared = model.prepare(c)
    wire = json.loads(prepared['messages'][1]['content'])['context']
    assert wire['schema_version'] == 'package-table-context/1.5'
    assert wire['questions'][0]['prompt'] == c['question_scopes'][0]['prompt']
    assert wire['questions'][0]['original_prompt'] == c['questions'][0]['prompt']
    assert wire['questions'][0]['options'] == c['questions'][0]['options']
    assert wire['questions'][1:] == c['questions'][1:]
    for field in ('materials', 'discussion'):
        for original, sent in zip(c[field], wire[field], strict=True):
            assert ''.join(p['text'] for p in sent['passages']) == original['text']
    assert prepared['source_context'] == before == c
    assert prepared['context_hash'] == content_hash(c)
    assert prepared['wire_context_hash'] == content_hash(wire)
    meta = model.metadata()
    assert meta['source_context_contract'] == c['schema_version']
    assert meta['finale_context_contract'] == wire['schema_version']
    assert meta['assessment_contract'] == 'table-evidence-assessment/1.2'
    assert 'CAST_BALLOT' not in prepared['messages'][0]['content']


def test_selected_wording_preserved_in_receipt_and_original_decision_projection():
    c = scoped_context(); model = ScopedPackageTableModel(object(), settings())
    value = assessment(c); result = model._read_output(canonical_json(value), model.prepare(c))
    Draft202012Validator(output_schema(c, SCOPED_MODEL_CONTRACT)).validate(value)
    assert result['assessment'] == value
    assert result['decision']['answers'][0]['option_ids'] == ['red']
    assert result['decision']['vote'] == value['vote']
    assert validate_evidence_decision(result['decision'], value, c) == value
    corrupted = deepcopy(result['decision']); corrupted['answers'][0]['option_ids'] = []
    with pytest.raises(ValueError, match='TABLE_EVIDENCE_DECISION_MISMATCH'):
        validate_evidence_decision(corrupted, value, c)


@pytest.mark.parametrize('wrong', ['red', '藏起红盒', '藏起红盒以保护别人', 'north', '藏起红盒以避免自己的经历被发现 '])
def test_partial_or_wrong_selected_wording_rejected_without_repair(wrong):
    c = scoped_context(); value = assessment(c)
    value['answers'][0]['selections'][0]['option_text'] = wrong
    model = ScopedPackageTableModel(object(), settings())
    with pytest.raises(ValueError, match='TABLE_SELECTED_OPTION_TEXT_MISMATCH'):
        model._read_output(canonical_json(value), model.prepare(c))
    assert value['answers'][0]['selections'][0]['option_text'] == wrong


@pytest.mark.parametrize('bad', ['missing', 'foreign', 'wronghash', 'wrongprompt', 'duplicate', 'extra'])
def test_scope_integrity_checked_before_provider_dispatch(bad):
    c = scoped_context(); scope = c['question_scopes'][0]
    if bad == 'missing': c.pop('question_scopes')
    elif bad == 'foreign': scope['basis'][0]['id'] = 'ungranted'
    elif bad == 'wronghash': scope['basis'][0]['text_sha256'] = '0' * 64
    elif bad == 'wrongprompt': scope['original_prompt_sha256'] = '0' * 64
    elif bad == 'duplicate': c['question_scopes'].append(deepcopy(scope))
    else: scope['answer'] = 'red'
    with pytest.raises(PackageRoleModelError, match='PACKAGE_TABLE_INPUT_INVALID'):
        ScopedPackageTableModel(object(), settings()).prepare(c)


def test_empty_sources_allow_only_unknown_and_never_force_a_selection():
    c = scoped_context(); c.update(materials=[], discussion=[], evidence_origins=[], question_scopes=[])
    value = assessment(c)
    for answer in value['answers']: answer['selections'] = []
    schema = Draft202012Validator(output_schema(c, SCOPED_MODEL_CONTRACT))
    assert schema.is_valid(value)
    model = ScopedPackageTableModel(object(), settings())
    assert model._read_output(canonical_json(value), model.prepare(c))['assessment'] == value
    bad = assessment(c)
    assert not schema.is_valid(bad)
    with pytest.raises(ValueError): model._read_output(canonical_json(bad), model.prepare(c))


def test_old_contexts_outputs_prepared_do_not_silently_upgrade():
    old = LocatedPackageTableModel(object(), settings()); new = ScopedPackageTableModel(object(), settings())
    old_c = located_context(); new_c = scoped_context()
    with pytest.raises(PackageRoleModelError): new.prepare(old_c)
    with pytest.raises(PackageRoleModelError): old.prepare(new_c)
    with pytest.raises(ValueError): new._read_output(canonical_json(prior_assessment()), new.prepare(new_c))
    with pytest.raises(ValueError): old._read_output(canonical_json(assessment(new_c)), old.prepare(old_c))
    assert asyncio.run(new.call(old.prepare(old_c)))['model_attempted'] is False
    assert asyncio.run(old.call(new.prepare(new_c)))['model_attempted'] is False


@pytest.mark.parametrize('action', ['CAST_BALLOT', 'BREAK_TIE'])
def test_nonfinale_prepared_payload_is_unchanged(action):
    c = context(); c.update(action=action, options=[dict(id='go', label='院子', cost=1)],
                            questions=[], accusation_options=[], trust_character_ids=[])
    assert ScopedPackageTableModel(object(), settings()).prepare(c) == LocatedPackageTableModel(object(), settings()).prepare(c)


def test_window_matches_actual_wire_including_scope_option_text_and_schema():
    c = scoped_context(); c['discussion'] = []
    model = ScopedPackageTableModel(object(), settings())
    frozen = model.prepare(c)
    size = len(canonical_json(frozen['messages']).encode()) + len(canonical_json(frozen['params']['response_format']).encode())
    assert table_context_window(c, size, SCOPED_MODEL_CONTRACT) == c
    with pytest.raises(ValueError): table_context_window(c, size - 1, SCOPED_MODEL_CONTRACT)

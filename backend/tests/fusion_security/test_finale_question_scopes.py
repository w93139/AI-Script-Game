"""Synthetic scope wording: source availability, ownership and frozen inputs."""
from copy import deepcopy
from hashlib import sha256

import pytest

from src.fusion.finale_question_scopes import (
    FinaleQuestionScopes, ScopeQuestion, apply_scopes, available_scopes,
)
from src.fusion.package_validation import canonical_json, content_hash
from src.fusion.structured_finale import StructuredFinale
from tests.fusion_security.test_package_full_play import full_package


def digest(text):
    return sha256(text.encode('utf-8')).hexdigest()


def fixture():
    package = full_package()
    package['knowledge'][0]['text'] = '此前的一次旅行里，你把蓝布包留在车站。\n日期尚未确定。'
    public = deepcopy(package['knowledge'][0])
    public.update(id='public-history', text='车站与今日案发的仓库是不同地点。',
                  visibility='PUBLIC', character_id=None, disclosure='PUBLIC')
    package['knowledge'].append(public)
    question = package['full_play']['finale']['questions'][0]
    document = {'schema_version': 'finale-question-scopes/1.0',
        'package_hash': content_hash(package), 'character_id': 'a', 'questions': [{
            'question_id': question['id'], 'original_prompt_sha256': digest(question['prompt']),
            'prompt': '本题指此前旅行中把蓝布包留在车站的往事。只选已有依据的判断，未知留空。',
            'basis': [{'collection': 'knowledge', 'id': item['id'], 'text_sha256': digest(item['text'])}
                      for item in (package['knowledge'][0], public)]}]}
    game = StructuredFinale(package['full_play']['finale'], {'fiction'},
        {m['id']: m['character_id'] for m in package['memories']},
        {t['id'] for t in package['truth']}, set())
    questions = game.view('a')['questions']
    materials = [{'collection': 'knowledge', 'id': m['id'], 'text': m['text'],
                  'kind': m['kind'], 'public': m['visibility'] == 'PUBLIC'}
                 for m in (package['knowledge'][0], public)]
    return package, document, questions, materials


def test_valid_catalogue_freezes_exact_document_and_changes_only_authorized_prompt():
    package, document, questions, materials = fixture()
    inputs = deepcopy((package, document, questions, materials))
    scopes = FinaleQuestionScopes(package, document)
    assert scopes.package_hash == content_hash(package) and scopes.character_id == 'a'
    assert scopes.revision == content_hash(document) and scopes.freeze() == document
    active = available_scopes(questions, materials, scopes.freeze()['questions'])
    assert active == document['questions']
    changed = apply_scopes(questions, materials, active)
    assert changed[0]['prompt'] == document['questions'][0]['prompt']
    assert {k: v for k, v in changed[0].items() if k != 'prompt'} == {
        k: v for k, v in questions[0].items() if k != 'prompt'}
    assert (package, document, questions, materials) == inputs
    assert 'SYSTEM_TRUTH' not in canonical_json(active + changed)
    assert all(key not in active[0] for key in ('options', 'answer', 'score', 'truth'))


def test_freeze_and_projection_do_not_retain_mutable_caller_aliases():
    package, document, questions, materials = fixture()
    scopes = FinaleQuestionScopes(package, document); frozen = scopes.freeze()
    document['questions'][0]['basis'].clear(); package['knowledge'][0]['text'] = 'changed'
    scopes.freeze()['questions'].clear()
    assert scopes.freeze() == frozen
    active = available_scopes(questions, materials, frozen['questions'])
    active[0]['basis'].clear()
    projected = apply_scopes(questions, materials, frozen['questions'])
    projected[0]['options'].clear()
    assert questions[0]['options'] and frozen['questions'][0]['basis']
    assert scopes.freeze() == frozen


@pytest.mark.parametrize('bad', [
    'version', 'extra_document', 'extra_question', 'options', 'extra_basis',
    'blank_prompt', 'empty_prompt', 'long_prompt', 'control_prompt', 'bidi_prompt',
    'empty_questions', 'empty_basis', 'duplicate_basis', 'duplicate_question',
    'collection_evidence', 'collection_memory', 'bad_digest', 'coerced_id',
])
def test_strict_document_rejects_ambiguous_or_changed_contract(bad):
    package, document, _, _ = fixture(); question = document['questions'][0]
    if bad == 'version': document['schema_version'] = 'finale-question-scopes/1.1'
    elif bad == 'extra_document': document['truth'] = 'do not read'
    elif bad == 'extra_question': question['answer'] = ['red']
    elif bad == 'options': question['options'] = [{'id': 'red', 'label': 'changed'}]
    elif bad == 'extra_basis': question['basis'][0]['text'] = 'injected source'
    elif bad == 'blank_prompt': question['prompt'] = ' \n\t'
    elif bad == 'empty_prompt': question['prompt'] = ''
    elif bad == 'long_prompt': question['prompt'] = '字' * 801
    elif bad == 'control_prompt': question['prompt'] += '\x00'
    elif bad == 'bidi_prompt': question['prompt'] += '\u202e'
    elif bad == 'empty_questions': document['questions'] = []
    elif bad == 'empty_basis': question['basis'] = []
    elif bad == 'duplicate_basis': question['basis'].append(deepcopy(question['basis'][0]))
    elif bad == 'duplicate_question': document['questions'].append(deepcopy(question))
    elif bad == 'collection_evidence': question['basis'][0]['collection'] = 'evidence'
    elif bad == 'collection_memory': question['basis'][0]['collection'] = 'memory'
    elif bad == 'bad_digest': question['basis'][0]['text_sha256'] = 'A' * 64
    else: question['question_id'] = 1
    with pytest.raises(ValueError): FinaleQuestionScopes(package, document)


@pytest.mark.parametrize('bad', [
    'package_hash', 'unknown_actor', 'unknown_question', 'foreign_question',
    'prompt_hash', 'unknown_source', 'foreign_private_source', 'truth_source',
    'public_with_owner', 'private_without_owner', 'source_hash',
    'duplicate_package_question', 'duplicate_package_source',
])
def test_catalogue_binds_question_and_source_to_package_and_role(bad):
    package, document, _, _ = fixture(); question = document['questions'][0]
    if bad == 'package_hash': document['package_hash'] = '0' * 64
    elif bad == 'unknown_actor': document['character_id'] = 'unknown'
    elif bad == 'unknown_question': question['question_id'] = 'unknown'
    elif bad == 'foreign_question': question['question_id'] = 'b-q'
    elif bad == 'prompt_hash': question['original_prompt_sha256'] = '0' * 64
    elif bad == 'unknown_source': question['basis'][0]['id'] = 'unknown'
    elif bad == 'foreign_private_source':
        question['basis'][0].update(id='initial-b', text_sha256=digest(package['knowledge'][1]['text']))
    elif bad == 'truth_source': question['basis'][0]['id'] = 'truth-main'
    elif bad == 'public_with_owner': package['knowledge'][-1]['character_id'] = 'b'
    elif bad == 'private_without_owner': package['knowledge'][0]['character_id'] = None
    elif bad == 'source_hash': question['basis'][0]['text_sha256'] = '0' * 64
    elif bad == 'duplicate_package_question': package['full_play']['finale']['questions'] *= 2
    else: package['knowledge'].append(deepcopy(package['knowledge'][0]))
    if bad != 'package_hash': document['package_hash'] = content_hash(package)
    with pytest.raises(ValueError): FinaleQuestionScopes(package, document)


@pytest.mark.parametrize('remaining', [[], [0], [1]])
def test_unacquired_basis_defers_whole_scope_and_keeps_original_question(remaining):
    package, document, questions, materials = fixture()
    scopes = FinaleQuestionScopes(package, document).freeze()['questions']
    acquired = [materials[i] for i in remaining]
    assert available_scopes(questions, acquired, scopes) == []
    assert apply_scopes(questions, acquired, scopes) == questions
    assert document['questions'][0]['prompt'] not in canonical_json(apply_scopes(questions, acquired, scopes))


@pytest.mark.parametrize('missing_first', [False, True])
def test_changed_acquired_text_fails_even_when_another_basis_is_missing(missing_first):
    _, document, questions, materials = fixture(); scopes = document['questions']
    if missing_first: scopes[0]['basis'].reverse()
    acquired = [deepcopy(materials[0])]; acquired[0]['text'] += '\n'
    with pytest.raises(ValueError, match='SOURCE_MISMATCH'):
        available_scopes(questions, acquired, scopes)


@pytest.mark.parametrize('bad', ['changed_prompt', 'missing_question', 'duplicate_question',
                                  'duplicate_scope', 'duplicate_material', 'wrong_type'])
def test_runtime_scope_integrity_rejects_ambiguous_or_changed_inputs(bad):
    _, document, questions, materials = fixture(); scopes = document['questions']
    if bad == 'changed_prompt': questions[0]['prompt'] += 'changed'
    elif bad == 'missing_question': questions.clear()
    elif bad == 'duplicate_question': questions *= 2
    elif bad == 'duplicate_scope': scopes *= 2
    elif bad == 'duplicate_material': materials *= 2
    else: scopes = tuple(scopes)
    with pytest.raises(ValueError): apply_scopes(questions, materials, scopes)


def test_scope_requires_exact_collection_and_does_not_search_equal_source_text():
    _, document, questions, materials = fixture()
    materials[0]['collection'] = 'evidence'
    materials.append({**materials[0], 'collection': 'knowledge', 'id': 'different-id'})
    assert available_scopes(questions, materials, document['questions']) == []


def test_filtered_choices_order_limits_and_other_questions_are_preserved():
    _, document, questions, materials = fixture()
    questions[0]['options'] = questions[0]['options'][1:2]
    questions[0]['max_choices'] = 1
    questions.append({'id': 'a-other', 'prompt': '另一个原题', 'options': [], 'max_choices': 0})
    scopes = [ScopeQuestion.model_validate(document['questions'][0])]
    result = apply_scopes(questions, materials, scopes)
    assert result[0]['options'] == questions[0]['options'] and result[0]['max_choices'] == 1
    assert result[1] == questions[1]
    assert apply_scopes(questions, materials, []) == questions
    assert result[0]['prompt'] != questions[0]['prompt']


def test_hashes_preserve_unicode_and_whitespace_without_normalizing_source():
    package, document, questions, materials = fixture()
    source = package['knowledge'][0]; source['text'] = 'Ａ\r\n旧事\t '
    document['package_hash'] = content_hash(package)
    document['questions'][0]['basis'][0]['text_sha256'] = digest(source['text'])
    materials[0]['text'] = source['text']
    scopes = FinaleQuestionScopes(package, document).freeze()['questions']
    assert available_scopes(questions, materials, scopes) == scopes
    materials[0]['text'] = 'A\n旧事'
    with pytest.raises(ValueError, match='SOURCE_MISMATCH'):
        available_scopes(questions, materials, scopes)

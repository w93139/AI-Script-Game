"""Finite scoped negation applies only to new authored topic contracts."""
import pytest

from src.fusion.package_play_rules import PlayRulesError
from src.fusion.topic_answer_checks import (
    NEGATION_VERSION, asserted_certainty, freeze_contract, validate_contract, validate_topic_answer,
)


def contract(version=NEGATION_VERSION, **updates):
    return {'schema_version': version, 'required_terms': [],
            'reject_unsupported_certainty': True, **updates}


def speech(text, basis=None):
    return {'segments': [{'mode': 'REPORT', 'text': text, 'basis': basis if basis is not None else [
        {'collection': 'evidence', 'id': 'box', 'passage_ids': ['p0001']}]}]}


SYNTHETIC_SCOPED_DENIAL = '也不能证明柜子里的钥匙肯定是我遗失的那把。'


@pytest.mark.parametrize('text', [
    SYNTHETIC_SCOPED_DENIAL,
    '我不能证明这笔钱肯定属于同一个人。',
    '目前我们也无法确认这枚硬币一定来自那个盒子。',
    '我目前还不能认定这条线索必然指向同一件事。',
    '暂时不能断定死亡地点肯定就是发现地点。',
    '无法证明他一定到过现场。',
    '现在我还不能确认柜子里的东西绝对没有变动。',
    '线索记载了盒中物品，也不能证明里面的钱肯定属于同一个人。',
])
def test_new_contract_accepts_finite_scoped_denial_of_certainty(text):
    assert asserted_certainty(text) is True
    assert asserted_certainty(text, allow_scoped_negation=True) is False
    validate_topic_answer(speech(text), {'answer_contract': contract()})


@pytest.mark.parametrize('version', [f'topic-answer-check/1.{n}' for n in range(4)])
def test_synthetic_scoped_denial_remains_rejected_by_every_old_version(version):
    with pytest.raises(PlayRulesError, match='CERTAINTY_UNSUPPORTED'):
        validate_topic_answer(speech(SYNTHETIC_SCOPED_DENIAL), {'answer_contract': contract(version)})


@pytest.mark.parametrize('text', [
    '我不能不证明这笔钱肯定是他的。',
    '我并非不能证明这笔钱肯定是他的。',
    '我不是无法确认这笔钱肯定是他的。',
    '我不是不能肯定是他。',
    '我并非无法肯定是他。',
    '我不能证明这笔钱不是不一定属于他。',
    '我无法证明这些钱但这肯定属于他。',
    '我无法证明这些钱可是这肯定属于他。',
    '我无法证明这些钱却肯定属于他。',
    '我无法证明这些钱其实肯定属于他。',
    '我无法证明这些钱所以肯定属于他。',
    '我无法证明这些钱我肯定属于他。',
    '我无法证明这些钱我们肯定属于他。',
    '我无法证明这些钱然而这些钱肯定属于他。',
    '我无法证明这些钱不一定属于他，但他肯定拿走了。',
    '不能证明这笔钱肯定属于他，但这一定是他干的。',
    '不能证明这笔钱肯定属于他。这个包一定属于他。',
    '不能证明这笔钱肯定属于他；他绝对拿过钱。',
    '不能证明这笔钱肯定属于他，这个人准是拿钱的人。',
    '不能证明这笔钱肯定属于他\n他必然拿走过钱。',
    '不能证明这笔钱肯定属于他而且一定就是他的。',
    '这笔钱肯定是同一笔。',
    '我听说不能证明这些钱肯定属于他。',
    '无法证明这件看起来像是有很多前因后果但实际上仍然未知的事情肯定如此。',
])
def test_scope_exception_does_not_hide_double_negation_transitions_or_new_assertions(text):
    assert asserted_certainty(text, allow_scoped_negation=True) is True
    with pytest.raises(PlayRulesError, match='CERTAINTY_UNSUPPORTED'):
        validate_topic_answer(speech(text), {'answer_contract': contract()})


@pytest.mark.parametrize('version', [f'topic-answer-check/1.{n}' for n in range(4)])
def test_legacy_direct_negation_behavior_is_unchanged(version):
    for text in ('不能肯定。', '不一定如此。', '不能说这肯定就是答案。'):
        validate_topic_answer(speech(text), {'answer_contract': contract(version)})
    # The new opt-in catches this additional double negative without changing
    # the historically narrower suffix check used by existing events.
    validate_topic_answer(speech('我不是不能肯定是他。'), {'answer_contract': contract(version)})


def test_new_contract_preserves_witness_question_disclosure_and_conditional_basis():
    materials = {('evidence', 'box'): {'text': '纸条记载：盒中放着几枚硬币。'}}
    authored = {'schema_version': NEGATION_VERSION, 'reject_unsupported_certainty': True,
                'reject_public_personal_observation': True, 'forbidden_terms': ['暗门'],
                'conditional_basis': [{'when_any': ['硬币'], 'requires': [
                    {'collection': 'evidence', 'id': 'box', 'passage_ids': ['p0001']}]}]}
    validate_contract(authored, materials, {'initial'})
    frozen = freeze_contract(authored, 'initial', [{'collection': 'evidence', 'id': 'box'}])
    validate_topic_answer(speech('我想问谁见过这些硬币？'), {'answer_contract': frozen})
    validate_topic_answer(speech('我不能证明这些硬币肯定来自同一个盒子。'), {'answer_contract': frozen})
    with pytest.raises(PlayRulesError, match='BASIS_INCOMPLETE'):
        validate_topic_answer(speech('不能证明这些硬币肯定来自同一个盒子。', basis=[]), {'answer_contract': frozen})
    with pytest.raises(PlayRulesError, match='DISCLOSURE_FORBIDDEN'):
        validate_topic_answer(speech('我想问谁见过暗门。'), {'answer_contract': frozen})
    with pytest.raises(PlayRulesError, match='PUBLIC_IS_NOT_PERSONAL'):
        validate_topic_answer(speech('我亲眼见过这些硬币。'), {'answer_contract': frozen})

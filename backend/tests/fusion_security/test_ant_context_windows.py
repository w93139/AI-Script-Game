"""Synthetic boundary cases for frozen Ant v2 request-window measurement."""
from copy import deepcopy
from dataclasses import replace

import pytest

from src.fusion.agents import PlayerModelSettings
from src.fusion.context_window import bounded_context
from src.fusion.package_call_model import PackageCallModel, AttributedPackageCallModel, call_window
from src.fusion.package_dialogue_model import (
    FullPackageDialogueModel, ScopedTaskPackageDialogueModel, FinaleMotivationModel,
    dialogue_context_window, finale_motivation_input_size,
)
from src.fusion.package_proposal_model import (
    FullPackageProposalModel, GuidedPackageProposalModel, proposal_context_window,
)
from src.fusion.package_table_model import PackageTableModel, BoundPackageTableModel, table_context_window
from src.fusion.package_validation import content_hash
from tests.fusion_security.test_attributed_call_model import context as phone_context
from tests.fusion_security.test_bound_table_model import context as table_context


KINDS = ('dialogue', 'scoped-dialogue', 'proposal', 'guided-proposal',
         'table', 'bound-table', 'call', 'attributed-call', 'finale', 'single-finale')
ANT_V2 = {'provider': 'ant_digital', 'provider_contract': 'ant-chat-qwen36-v2'}


def case(kind):
    phone = phone_context()
    common = {k: deepcopy(phone[k]) for k in (
        'play_id', 'package_hash', 'revision', 'character', 'current_phase', 'discussion', 'history_window')}
    if kind in ('dialogue', 'scoped-dialogue'):
        cls = ScopedTaskPackageDialogueModel if kind == 'scoped-dialogue' else FullPackageDialogueModel
        context = dict(common, schema_version='package-dialogue-context/1.1', channel='PUBLIC',
                       materials=deepcopy(phone['materials']), reply_to='claim-3')
        if kind == 'scoped-dialogue':
            context.update(schema_version='package-dialogue-context/1.4', strategy_materials=[],
                           material_scope='ALL_AUTHORIZED')
        window = lambda c, limit, binding: dialogue_context_window(c, limit, cls.model_contract, binding)
    elif kind in ('proposal', 'guided-proposal'):
        cls = GuidedPackageProposalModel if kind == 'guided-proposal' else FullPackageProposalModel
        context = dict(common, schema_version='package-investigation-context/1.1', materials=[],
                       options=[{'id': 'garden', 'label': '庭院', 'cost': 1}])
        version = 'package-proposal-model/1.2' if kind == 'guided-proposal' else 'package-proposal-model/1.1'
        window = lambda c, limit, binding: proposal_context_window(c, limit, version, binding)
    elif kind in ('table', 'bound-table'):
        cls = BoundPackageTableModel if kind == 'bound-table' else PackageTableModel
        context = table_context()
        window = lambda c, limit, binding: table_context_window(c, limit, cls.model_contract, binding)
    elif kind in ('call', 'attributed-call'):
        cls = AttributedPackageCallModel if kind == 'attributed-call' else PackageCallModel
        context = phone
        if kind == 'call':
            context['schema_version'] = 'package-call-context/1.0'
            context.pop('strategy_materials')
        window = lambda c, limit, binding: call_window(c, limit, cls.model_contract, binding)
    else:
        cls = FinaleMotivationModel
        context = dict(common, schema_version='finale-motivation-context/' + ('1.3' if kind == 'single-finale' else '1.2'), materials=[], evidence_origins=[])
        window = lambda c, limit, binding: bounded_context(
            c, limit, lambda value: finale_motivation_input_size(value, binding))
    context['revision'] = 20
    context['discussion'] = [{'id': f'claim-{i}', 'sequence': i, 'speaker': 'c' if i == 3 else 'a', 'kind': 'CLAIM',
                              'text': '这是一段用来验证输入长度的合成讨论。' * 30} for i in range(1, 7)]
    settings = PlayerModelSettings('ant_digital', 'qwen3.6-plus', 10, 0, 1000, 98304, 'disabled', 0, True)
    model = cls(object(), settings, policy='finale-motivation/' + ('1.3' if kind == 'single-finale' else '1.2')) if kind in ('finale', 'single-finale') else cls(object(), settings)
    return context, model, window


@pytest.mark.parametrize('kind', KINDS)
def test_ant_v2_window_trims_history_for_actual_wire_size_and_preserves_authorized_materials(kind):
    context, model, window = case(kind)
    original = deepcopy(context)
    full = window(context, 98304, ANT_V2)
    limit = model.prepare(full)['input_tokens'] - 4096 - 1
    selected = window(context, limit, ANT_V2)
    assert len(selected['discussion']) < len(full['discussion'])
    assert selected['history_window']['omitted_count'] == len(context['discussion']) - len(selected['discussion'])
    assert selected['materials'] == context['materials']
    if context.get('reply_to'):
        assert context['reply_to'] in {item['id'] for item in selected['discussion']}
    model.settings = replace(model.settings, max_input_bytes=limit)
    prepared = model.prepare(selected)
    assert prepared['input_tokens'] <= limit + 4096
    assert context == original


@pytest.mark.parametrize('kind', KINDS)
def test_ant_v2_required_material_limit_fails_before_dispatch_instead_of_dropping_it(kind):
    context, model, window = case(kind)
    context['discussion'] = [item for item in context['discussion'] if item['id'] == context.get('reply_to')]
    full = window(context, 98304, ANT_V2)
    required_bytes = model.prepare(full)['input_tokens'] - 4096
    assert window(context, required_bytes, ANT_V2) == full
    with pytest.raises(ValueError, match='REQUIRED_CONTEXT_TOO_LARGE'):
        window(context, required_bytes - 1, ANT_V2)


@pytest.mark.parametrize('kind', KINDS)
def test_old_provider_and_ant_v1_window_hashes_are_unchanged_by_current_ant_profile(kind):
    context, _, window = case(kind)
    # A restrictive boundary exercises historical selection, not just a roomy
    # no-op window. The omitted-count and exact selected text are hashed too.
    full = window(context, 98304, None)
    pinned = {context.get('reply_to')}
    context['discussion'] = [item for item in full['discussion'] if item['id'] in pinned]
    minimum = window(context, 98304, None)
    context = full
    # Find one historical boundary without importing process configuration.
    for limit in range(1024, 20000, 256):
        try:
            old = window(context, limit, None)
        except ValueError:
            continue
        if len(old['discussion']) < len(full['discussion']):
            break
    else:
        pytest.fail('synthetic fixture did not reach a trimming boundary')
    assert len(old['discussion']) >= len(minimum['discussion'])
    old_hash = content_hash(old)
    for provider, contract in [('ant_digital', 'ant-chat-qwen36-v1'),
                               ('volcengine_ark', 'ark-chat-character-v2'),
                               ('aliyun_bailian', 'bailian-chat-qwen37-v2'),
                               ('volcengine_ark', 'ant-chat-qwen36-v2')]:
        assert content_hash(window(context, limit, {'provider': provider, 'provider_contract': contract})) == old_hash

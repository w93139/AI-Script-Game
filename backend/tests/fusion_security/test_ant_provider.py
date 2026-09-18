"""Ant configuration boundaries; all credentials and replies are synthetic."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.fusion.agents import PlayerModelSettings
from src.fusion.budget import BudgetPolicy
from src.fusion.package_role_model import PackageRoleModel
from src.fusion.provider_config import load_selected_config, SmokeConfigurationError
from src.fusion.providers import PLAYER_PROVIDER_PROFILES
from src.services.llm_service import LLMResponse
from tests.fusion_security.test_package_play_rules import play_package
from src.fusion.package_play_rules import PackagePlayRules


def test_ant_reads_only_its_credential_and_prices(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    values = {
        'ANT_MAAS_API_KEY': 'synthetic-ant',
        'ANT_MAAS_QWEN_INPUT_COST_PER_MILLION': '2',
        'ANT_MAAS_QWEN_CACHED_INPUT_COST_PER_MILLION': '2',
        'ANT_MAAS_QWEN_OUTPUT_COST_PER_MILLION': '12',
        'ANT_MAAS_QWEN_PRICING_VERSION': 'fixture-ant',
        'ARK_API_KEY': 'synthetic-other',
        'ARK_CHARACTER_OUTPUT_COST_PER_MILLION': '999',
    }
    env.write_text('\n'.join(f'{k}={v}' for k, v in values.items()))
    config = load_selected_config('ant_digital', env)
    assert config.api_key == 'synthetic-ant'
    assert config.model == 'qwen3.6-plus'
    assert config.pricing.price(1_000_000, 1_000_000) == 14
    for k, v in values.items():
        monkeypatch.setenv(k, v)
    assert BudgetPolicy.from_env('ant_digital').output_rate_cny == 12
    env.write_text('\n'.join(f'{k}={v}' for k, v in values.items() if k != 'ANT_MAAS_API_KEY'))
    with pytest.raises(SmokeConfigurationError, match='SELECTED_API_KEY_REQUIRED'):
        load_selected_config('ant_digital', env)


@pytest.mark.parametrize('override,expected', [
    ({'model': 'qwen3.8-flash'}, 'PACKAGE_ROLE_MODEL_UNSUPPORTED'),
    ({'paid_calls_enabled': False}, 'PACKAGE_ROLE_MODEL_DISABLED'),
])
def test_ant_unapproved_model_or_paid_off_never_dispatches(override, expected):
    profile = PLAYER_PROVIDER_PROFILES['ant_digital']
    settings = PlayerModelSettings('ant_digital', profile.default_model, 10, 0, 1000, 20000, 'disabled', .7, True)
    client = SimpleNamespace(chat_completion=AsyncMock())
    model = PackageRoleModel(client, replace(settings, **override))
    assert model.unavailable_reason == expected
    assert not asyncio.run(model.call({}))['model_attempted']
    client.chat_completion.assert_not_awaited()


def test_ant_unknown_result_is_not_retried_and_different_response_model_is_rejected():
    settings = PlayerModelSettings('ant_digital', 'qwen3.6-plus', 10, 3, 1000, 20000, 'disabled', .7, True)
    client = SimpleNamespace(chat_completion=AsyncMock(side_effect=TimeoutError()))
    model = PackageRoleModel(client, settings)
    prepared = model.prepare(PackagePlayRules(play_package(), 'a').role_context('b'), '相关线索？')
    assert asyncio.run(model.call(prepared))['status'] == 'UNKNOWN'
    assert client.chat_completion.await_count == 1
    client.chat_completion.reset_mock(side_effect=True)
    client.chat_completion.return_value = LLMResponse('{"refs":[]}', model='other-model',
        usage={'prompt_tokens': 20, 'completion_tokens': 10}, finish_reason='stop')
    assert asyncio.run(model.call(prepared))['error_code'] == 'PACKAGE_ROLE_MODEL_MISMATCH'
    assert client.chat_completion.await_count == 1


@pytest.mark.parametrize('kind', ['role', 'dialogue', 'proposal', 'table', 'call', 'finale'])
def test_ant_all_game_requests_contain_json_instruction_and_count_its_bytes(kind):
    from copy import deepcopy
    from src.fusion.package_dialogue_model import PackageDialogueModel, FinaleMotivationModel
    from src.fusion.package_proposal_model import PackageProposalModel
    from src.fusion.package_table_model import BoundPackageTableModel
    from src.fusion.package_call_model import AttributedPackageCallModel
    from src.fusion.package_validation import canonical_json
    from tests.fusion_security.test_attributed_call_model import context as phone_context
    from tests.fusion_security.test_bound_table_model import context as table_context
    base = phone_context()
    common = {k: deepcopy(base[k]) for k in (
        'play_id', 'package_hash', 'revision', 'character', 'current_phase', 'discussion')}
    if kind == 'role':
        cls, context, args = PackageRoleModel, PackagePlayRules(play_package(), 'a').role_context('b'), ('线索？',)
    elif kind == 'dialogue':
        cls, context, args = PackageDialogueModel, dict(common, schema_version='package-dialogue-context/1.0',
            materials=[], reply_to='claim-3'), ()
    elif kind == 'proposal':
        cls, context, args = PackageProposalModel, dict(common, schema_version='package-investigation-context/1.0',
            materials=[], options=[{'id':'garden','label':'庭院','cost':1}]), ()
    elif kind == 'table':
        cls, context, args = BoundPackageTableModel, table_context(), ()
    elif kind == 'call':
        cls, context, args = AttributedPackageCallModel, base, ()
    else:
        cls, context, args = FinaleMotivationModel, dict(common, schema_version='finale-motivation-context/1.0',
            materials=[], history_window=base['history_window']), ()
    limit = cls.input_byte_ceiling
    settings = PlayerModelSettings('ant_digital', 'qwen3.6-plus', 10, 0, 1000, limit, 'disabled', 0, True)
    model = cls(object(), settings)
    prepared = model.prepare(context, *args)
    assert 'JSON' in prepared['messages'][0]['content']
    assert '请严格只输出 JSON 对象，遵循要求的字段和引用约束。' in prepared['messages'][0]['content']
    if kind != 'role':
        assert prepared['messages'][0]['content'].endswith(canonical_json(prepared['params']['response_format']['json_schema']['schema']))
    assert model.metadata()['provider_contract'] == 'ant-chat-qwen36-v2'
    actual = len(canonical_json(prepared['messages']).encode())
    if kind != 'role': actual += len(canonical_json(prepared['params']['response_format']).encode())
    assert prepared['input_tokens'] == actual + 4096
    # The adapter validates its actual wire size, including the provider note.
    if actual > 1024:
        too_small = cls(object(), replace(settings, max_input_bytes=actual - 1))
        with pytest.raises(ValueError, match='INPUT_TOO_LARGE'):
            too_small.prepare(context, *args)


@pytest.mark.parametrize('name', ['volcengine_ark', 'aliyun_bailian'])
def test_old_provider_prompt_remains_byte_identical(name):
    original = '只输出约定字段。'
    assert PLAYER_PROVIDER_PROFILES[name].prompt_for_wire(original) == original
    assert PLAYER_PROVIDER_PROFILES[name].prompt_for_wire(original, {'type': 'object'}) == original

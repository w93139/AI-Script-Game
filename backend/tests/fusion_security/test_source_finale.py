"""Synthetic public source protocol; structure is not semantic acceptance."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from src.fusion.located_evidence import source_wire_context, source_passage_index, authorized_evidence_origins
from src.fusion.source_finale import POLICY, source_finale_schema, resolve_finale_sources
from src.fusion.package_dialogue_model import FinaleMotivationModel, validate_finale_motivation, finale_motivation_input_size, PROMPTS
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_finale_motivation import play, runtime, enter_finale, service, answer, output, events, careful_context
from tests.fusion_security.test_finale_evidence import supported as old_supported


def supported(context):
    address = next(iter(source_passage_index(context)))
    return {'text': '我怀疑 a，公开记录中的线索仍待核对。', 'assessment': {
        'facts': [{'source_id': address, 'point': '公开记录中的线索。'}],
        'relation': 'OBSERVATION', 'event_relation': 'UNKNOWN', 'time_relation': 'UNKNOWN',
        'identity_relation': 'UNKNOWN', 'exclusive': False}}


def restore(wire):
    c = deepcopy(wire)
    for field in ('materials', 'discussion'):
        for item in c[field]: item['text'] = ''.join(p['text'] for p in item.pop('passages'))
    return c


@pytest.mark.parametrize('text', ['  指引。\n\n正文带时间限定。\r\n', '字' * 1200, '字' * 1201 + '\n\n尾段。', '\t\n'])
def test_card_text_is_lossless_and_addresses_stable_under_reordering(text):
    c = careful_context('1.6'); c['materials'][0]['text'] = text
    c['materials'].append({'collection': 'knowledge', 'id': 'note', 'text': '同名不同材料。\n\n下一段。'})
    before = deepcopy(c); wire = source_wire_context(c); index = source_passage_index(c)
    for field in ('materials', 'discussion'):
        for original, sent in zip(c[field], wire[field]):
            assert ''.join(p['text'] for p in sent['passages']) == original['text']
    if len(text) <= 1200: assert wire['materials'][0]['passages'] == [{'id': 'e:note/p1', 'text': text}]
    c['materials'].reverse(); c['discussion'].reverse()
    assert source_passage_index(c) == index
    assert 'k:note/p1' in index and 'e:note/p1' in index
    assert source_wire_context(before) == wire


def test_server_resolves_only_selected_source_and_never_repairs_model_meaning():
    c = careful_context('1.6')
    c['materials'] += [{'collection': 'evidence', 'id': 'wrong-card', 'text': '一只木盒。'},
                       {'collection': 'knowledge', 'id': 'map', 'text': '先读指引。\n\n甲地。\n\n乙地。'}]
    raw = supported(c); raw['assessment']['facts'][0] = {'source_id': 'e:wrong-card/p1', 'point': '旅客预订房间。'}
    assert resolve_finale_sources(raw, c)[0]['text'] == '一只木盒。'
    # A valid address does not prove the point: independent source review must
    # reject this semantic mismatch, not silently swap in the matching card.
    assert validate_finale_motivation(raw, c) == raw
    raw['assessment']['facts'][0]['source_id'] = 'k:map/p2'
    assert resolve_finale_sources(raw, c)[0]['text'].strip() == '甲地。'
    raw['assessment']['facts'][0]['source_id'] = 'k:map/p99'
    with pytest.raises(ValueError): validate_finale_motivation(raw, c)


@pytest.mark.parametrize('kind', ['foreign', 'memory', 'blank_point', 'duplicate', 'quote', 'basis', 'unknown_nonempty', 'empty_fact', 'exclusive', 'link_one', 'bad_conflict'])
def test_invalid_source_or_relationship_is_rejected_without_repair(kind):
    c = careful_context('1.6'); raw = supported(c); fact = raw['assessment']['facts'][0]
    if kind == 'foreign': fact['source_id'] = 'e:missing/p1'
    elif kind == 'memory':
        c['materials'].append({'collection': 'memory', 'id': 'secret', 'text': '不公开。'})
        fact['source_id'] = 'm:secret/p1'
    elif kind == 'blank_point': fact['point'] = '  '
    elif kind == 'duplicate': raw['assessment']['facts'] *= 2
    elif kind == 'quote': fact['excerpt'] = '模型不应复制摘录'
    elif kind == 'basis': raw['basis'] = [{'collection': 'evidence', 'id': 'note'}]
    elif kind == 'unknown_nonempty': raw['assessment']['relation'] = 'UNKNOWN'
    elif kind == 'empty_fact': raw['assessment']['facts'] = []
    elif kind == 'exclusive': raw['assessment']['exclusive'] = True
    elif kind == 'link_one': raw['assessment']['relation'] = 'POSSIBLE_LINK'
    else: raw['assessment'].update(relation='CONFLICT', exclusive=True)
    before = deepcopy(raw)
    with pytest.raises(ValueError): validate_finale_motivation(raw, c)
    assert raw == before


@pytest.mark.parametrize('relation,event,time', [('CONFLICT', 'SAME', 'OVERLAP'), ('CONFLICT', 'DIFFERENT', 'PERSISTENT_FACT'), ('POSSIBLE_LINK', 'UNKNOWN', 'UNKNOWN')])
def test_two_facts_from_same_card_are_representable_not_automatically_semantically_proven(relation, event, time):
    c = careful_context('1.6'); raw = supported(c)
    raw['assessment']['facts'].append({'source_id': 'e:note/p1', 'point': '同一来源另一项带限定的事实。'})
    raw['assessment'].update(relation=relation, event_relation=event, time_relation=time,
                             identity_relation='SAME', exclusive=relation == 'CONFLICT')
    Draft202012Validator(source_finale_schema(c)).validate(raw)
    assert validate_finale_motivation(raw, c) == raw


def test_canonical_unknown_and_schema_enum_exclude_unseen_or_memory_sources():
    c = careful_context('1.6'); raw = supported(c)
    raw.update(text=''); raw['assessment'].update(facts=[], relation='UNKNOWN')
    assert validate_finale_motivation(raw, c) == raw
    Draft202012Validator(source_finale_schema(c)).validate(raw)
    schema = source_finale_schema(c)
    assert set(schema['$defs']['SourceFinaleFact']['properties']['source_id']['enum']) == set(source_passage_index(c))
    c.update(materials=[], discussion=[], evidence_origins=[])
    schema = source_finale_schema(c)
    assert len(schema['$defs']['SourceFinaleAssessment']['anyOf']) == 1
    Draft202012Validator(schema).validate(raw)


def test_origin_projection_excludes_unseen_future_and_unlock_prerequisites():
    package = {'mechanics': {'actions': [dict(id='unlock', label='先决地点'), dict(id='find', label='发现地点'),
        dict(id='future', label='未来地点')]}, 'evidence': [
        dict(id='visible', release={'required_action_ids': ['find', 'future']}),
        dict(id='unseen', release={'required_action_ids': ['unlock']}),
        dict(id='no-origin', release={})]}
    engine = SimpleNamespace(_package=package, state=lambda: {'completed_action_ids': ['unlock', 'find']})
    materials = [dict(collection='evidence', id='visible'), dict(collection='knowledge', id='unseen'), dict(collection='evidence', id='no-origin')]
    assert authorized_evidence_origins(engine, materials) == [dict(id='visible', labels=['发现地点']), dict(id='no-origin', labels=[])]


@pytest.mark.parametrize('provider,model', [('volcengine_ark', 'doubao-seed-character-260628'), ('ant_digital', 'qwen3.6-plus')])
def test_exact_wire_meter_frozen_sources_and_tamper_refusal(play, provider, model):
    play.test_finale_policy = POLICY; _, _, view = enter_finale(play)
    row = play.play._row(view['play_id'], 1); package, binding = play.play._resolve(row)
    c = play.play._finale_context(play.play._replay(row, package, binding), binding, 'b')
    adapter = FinaleMotivationModel(play.sdk, replace(play.model.settings, provider=provider, model=model,
        max_input_bytes=98304, max_output_tokens=1024), POLICY)
    frozen = adapter.prepare(c); wire = json.loads(frozen['messages'][1]['content'])['context']
    assert restore(wire) == c and frozen['source_context'] == c
    assert frozen['context_hash'] == content_hash(c)
    assert frozen['input_tokens'] == finale_motivation_input_size(c, adapter.metadata()) + 4096
    assert frozen['input_tokens'] - 4096 == len(canonical_json(frozen['messages']).encode()) + len(canonical_json(frozen['params']['response_format']).encode())
    Draft202012Validator(frozen['params']['response_format']['json_schema']['schema']).validate(supported(c))
    for key in ('PRIVATE_BOOK_', 'PRIVATE_MEMORY_', 'SYSTEM_TRUTH', 'answer_key', 'questions'):
        assert key not in canonical_json(wire)
    for change in ('source', 'wire', 'schema', 'limit'):
        bad = deepcopy(frozen)
        if change == 'source': bad['source_context']['materials'][0]['text'] += '改变'
        elif change == 'wire': bad['messages'][1]['content'] += ' '
        elif change == 'schema': bad['params']['response_format']['json_schema']['schema'] = {}
        else: bad['output_tokens'] += 1
        assert asyncio.run(adapter.call(bad))['model_attempted'] is False
    play.sdk.chat_completion.assert_not_awaited()


@pytest.mark.parametrize('human', list('abcde'))
def test_four_public_results_refresh_without_dispatch_or_private_audit_leak(play, human):
    play.test_finale_policy = POLICY; _, _, view = enter_finale(play, human)
    row = play.play._row(view['play_id'], 1); package, binding = play.play._resolve(row)
    original = deepcopy(play.play._replay(row, package, binding).engine.state())
    async def sdk(messages, **params):
        wire = json.loads(messages[1].content)['context']
        assert params['max_tokens'] == 1024
        return output(supported(restore(wire)))
    play.sdk.chat_completion.side_effect = sdk
    done = asyncio.run(play.play.complete_finale_motivations(view['play_id'], 1))
    assert done['finale_motivation']['complete'] and all(e['text'] for e in done['finale_speeches'])
    assert 'assessment' not in canonical_json(done) and 'source_id' not in canonical_json(done)
    results = [json.loads(e.event_json)['data'] for e in events(play) if json.loads(e.event_json)['kind'] == 'AI_RESULT']
    assert len(results) == 4 and all(r['motivation']['assessment']['facts'] for r in results)
    assert play.play._replay(row, package, binding).engine.state() == original
    assert service(play).get(view['play_id'], 1) == done
    assert asyncio.run(service(play).complete_finale_motivations(view['play_id'], 1)) == done
    assert play.sdk.chat_completion.await_count == 4


@pytest.mark.parametrize('version', ['1.0', '1.1', '1.2', '1.3', '1.4', '1.5'])
@pytest.mark.parametrize('pending', [False, True])
def test_old_ready_and_pending_requests_remain_frozen_after_new_default(play, version, pending):
    old = 'finale-motivation/' + version
    play.test_finale_policy = old; _, _, view = enter_finale(play)
    if pending: assert play.play._begin_finale_motivation(view['play_id'], 'b', 1)[1]
    saved = [(e.event_json, e.event_hash, e.state_hash) for e in events(play)]
    play.test_finale_policy = POLICY; newer = service(play)
    async def sdk(messages, **params):
        assert messages[0].content == PROMPTS[old]
        assert params['max_tokens'] == (1024 if version == '1.5' else 192)
        c = json.loads(messages[1].content)['context']
        assert c['schema_version'] == 'finale-motivation-context/' + version
        return output(old_supported(restore(c)) if version == '1.5' else answer())
    play.sdk.chat_completion.side_effect = sdk
    if pending:
        waiting = asyncio.run(newer.complete_finale_motivations(view['play_id'], 1))
        assert waiting['pending_ai'] and play.sdk.chat_completion.await_count == 0
        play.clock[0] += 301
    done = asyncio.run(newer.complete_finale_motivations(view['play_id'], 1))
    assert done['finale_motivation']['complete']
    assert play.sdk.chat_completion.await_count == (3 if pending else 4)
    assert [(e.event_json, e.event_hash, e.state_hash) for e in events(play)][:len(saved)] == saved
    assert newer.get(view['play_id'], 1) == done


@pytest.mark.parametrize('kind', ['unknown_text', 'known_empty', 'trailing_point', 'duplicate_fact'])
def test_schema_and_validator_reject_empty_relationship_mismatch(kind):
    c = careful_context('1.6'); raw = supported(c)
    if kind == 'unknown_text': raw['assessment'].update(relation='UNKNOWN', facts=[])
    elif kind == 'known_empty': raw['text'] = ''
    elif kind == 'trailing_point': raw['assessment']['facts'][0]['point'] += ' '
    else: raw['assessment']['facts'] *= 2
    with pytest.raises(ValueError): validate_finale_motivation(raw, c)
    assert not Draft202012Validator(source_finale_schema(c)).is_valid(raw)


def test_unselected_paragraph_cannot_authorize_a_known_location():
    c = careful_context('1.6'); c['materials'][0]['collection'] = 'knowledge'
    c['materials'][0]['text'] = '早晨的观察。\n\n登记处有记录。'
    raw = supported(c); raw['text'] = '我怀疑 a，登记处的记录值得核对。'
    assert raw['assessment']['facts'][0]['source_id'] == 'k:note/p1'
    with pytest.raises(ValueError, match='LOCATION_UNSUPPORTED'): validate_finale_motivation(raw, c)
    raw['assessment']['facts'][0]['source_id'] = 'k:note/p2'
    assert validate_finale_motivation(raw, c) == raw

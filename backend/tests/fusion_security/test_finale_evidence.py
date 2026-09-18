"""Evidence finale: synthetic sources, frozen old wires and private-only audit."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from src.fusion.package_dialogue_model import (
    FinaleMotivationModel, EvidenceFinaleMotivationOutput, PROMPTS,
    validate_finale_motivation, finale_motivation_input_size,
)
from src.fusion.table_evidence import evidence_passage_index
from src.fusion.package_validation import canonical_json, content_hash
from tests.fusion_security.test_finale_motivation import (
    play, runtime, enter_finale, service, answer, output, events, careful_context,
)


def assessment(facts=(), relation='OBSERVATION', **kw):
    return dict(facts=list(facts), relation=relation, event_relation='UNKNOWN',
                time_relation='UNKNOWN', identity_relation='UNKNOWN', exclusive=False, **kw)


def supported(context):
    key, span = next(iter(evidence_passage_index(context).items()))
    return {'text': '我怀疑 a，公开记录中的线索仍待核对。',
            'basis': [{'collection': span['collection'], 'id': span['id']}],
            'assessment': assessment([{'passage_id': key, 'excerpt': span['text'][:120]}])}


def test_excerpt_integrity_and_unknown_without_repair():
    ctx = careful_context('1.5'); raw = supported(ctx)
    assert validate_finale_motivation(raw, ctx) == raw
    unknown = dict(text='', basis=[], assessment=assessment(relation='UNKNOWN'))
    assert validate_finale_motivation(unknown, ctx) == unknown
    for change in ('foreign', 'invented', 'missing', 'extra', 'false-unknown', 'empty'):
        bad = deepcopy(raw)
        if change == 'foreign': bad['assessment']['facts'][0]['passage_id'] = 'm9999.p0001'
        elif change == 'invented': bad['assessment']['facts'][0]['excerpt'] = '从未提供的证词。'
        elif change == 'missing': bad['basis'] = []
        elif change == 'extra': bad['basis'].append({'collection': 'discussion', 'id': 'claim-old'})
        elif change == 'false-unknown': bad['assessment']['relation'] = 'UNKNOWN'
        else: bad['assessment']['facts'][0]['excerpt'] = ' '
        with pytest.raises(ValueError): validate_finale_motivation(bad, ctx)


@pytest.mark.parametrize('field,value', [
    ('event_relation', 'DIFFERENT'), ('event_relation', 'UNKNOWN'),
    ('time_relation', 'SEQUENCE'), ('time_relation', 'UNKNOWN'),
    ('identity_relation', 'SIMILAR'), ('identity_relation', 'UNKNOWN'),
    ('exclusive', False), ('facts', []),
])
def test_conflict_requires_explicit_same_event_overlap_identity_and_exclusion(field, value):
    ctx = careful_context('1.5')
    raw = {'text': '我怀疑 b，他说的记录仍待核对。',
           'basis': [{'collection': 'discussion', 'id': 'claim-old'}, {'collection': 'discussion', 'id': 'claim-recent'}],
           'assessment': dict(facts=[{'passage_id': f'd000{i+1}.p0001', 'excerpt': d['text']} for i,d in enumerate(ctx['discussion'])],
                              relation='CONFLICT', event_relation='SAME', time_relation='OVERLAP', identity_relation='SAME', exclusive=True)}
    # Even consistent labels are assertions only; the two synthetic statements
    # actually concern different times, which still needs source review.
    raw['assessment'][field] = value
    with pytest.raises(ValueError): validate_finale_motivation(raw, ctx)


@pytest.mark.parametrize('provider,model', [('volcengine_ark', 'doubao-seed-character-260628'), ('ant_digital', 'qwen3.6-plus')])
def test_lossless_public_wire_private_free_meter_and_tamper_refusal(play, provider, model):
    play.test_finale_policy = 'finale-motivation/1.5'
    _, _, view = enter_finale(play)
    row = play.play._row(view['play_id'], 1); _, binding = play.play._resolve(row)
    state = play.play._replay(row, play.play._resolve(row)[0], binding)
    context = play.play._finale_context(state, binding, 'b')
    context['materials'][0]['text'] = '  昨日记录。\n\n  今日说明。\n '
    adapter = FinaleMotivationModel(play.sdk, replace(play.model.settings,
        provider=provider, model=model, max_input_bytes=98304, max_output_tokens=1024), 'finale-motivation/1.5')
    # Test profiles use an injected SDK; no configured key is sent.
    prepared = adapter.prepare(context)
    wire = json.loads(prepared['messages'][1]['content'])['context']
    for original, sent in zip(context['materials'], wire['materials']):
        assert ''.join(p['text'] for p in sent['passages']) == original['text']
        assert 'text' not in sent
    assert prepared['source_context'] == context
    assert prepared['context_hash'] == content_hash(context)
    assert prepared['input_tokens'] == finale_motivation_input_size(context, adapter.metadata()) + 4096
    assert prepared['input_tokens'] - 4096 == len(canonical_json(prepared['messages']).encode()) + len(canonical_json(prepared['params']['response_format']).encode())
    assert prepared['params']['response_format']['json_schema']['schema'] == EvidenceFinaleMotivationOutput.model_json_schema()
    assert 'PRIVATE_BOOK_' not in canonical_json(wire) and 'SYSTEM_TRUTH' not in canonical_json(wire)
    for change in ('source', 'wire', 'budget', 'hash'):
        bad = deepcopy(prepared)
        if change == 'source': bad['source_context']['materials'][0]['text'] += '追加'
        elif change == 'wire': bad['messages'][1]['content'] += ' '
        elif change == 'budget': bad['output_tokens'] += 1
        else: bad['context_hash'] = '0' * 64
        assert asyncio.run(adapter.call(bad))['model_attempted'] is False
    play.sdk.chat_completion.assert_not_awaited()


def test_new_public_four_results_are_private_auditable_and_refresh_does_not_dispatch(play):
    play.test_finale_policy = 'finale-motivation/1.5'; _, _, view = enter_finale(play)
    row = play.play._row(view['play_id'], 1); package, binding = play.play._resolve(row)
    original = deepcopy(play.play._replay(row, package, binding).engine.state())
    async def sdk(messages, **params):
        wire = json.loads(messages[1].content)['context']
        assert params['max_tokens'] == 1024
        context = deepcopy(wire)
        for m in context['materials']: m['text'] = ''.join(p['text'] for p in m.pop('passages'))
        for d in context['discussion']: d['text'] = ''.join(p['text'] for p in d.pop('passages'))
        return output(supported(context))
    play.sdk.chat_completion.side_effect = sdk
    done = asyncio.run(play.play.complete_finale_motivations(view['play_id'], 1))
    assert done['finale_motivation']['complete'] and all(e['text'] for e in done['finale_speeches'])
    assert 'assessment' not in canonical_json(done) and 'passage_id' not in canonical_json(done)
    results = [json.loads(e.event_json)['data'] for e in events(play) if json.loads(e.event_json)['kind'] == 'AI_RESULT']
    assert len(results) == 4 and all(r['motivation']['assessment']['facts'] for r in results)
    assert play.play._replay(row, package, binding).engine.state() == original
    assert service(play).get(view['play_id'], 1) == done
    assert asyncio.run(service(play).complete_finale_motivations(view['play_id'], 1)) == done
    assert play.sdk.chat_completion.await_count == 4


@pytest.mark.parametrize('version', ['1.0', '1.1', '1.2', '1.3', '1.4'])
@pytest.mark.parametrize('pending', [False, True])
def test_new_output_limit_does_not_change_old_unfinished_wire_or_retry_pending(play, version, pending):
    old = 'finale-motivation/' + version
    play.test_finale_policy = old; _, _, view = enter_finale(play)
    if pending: assert play.play._begin_finale_motivation(view['play_id'], 'b', 1)[1]
    saved = [(e.event_json, e.event_hash, e.state_hash) for e in events(play)]
    play.test_finale_policy = 'finale-motivation/1.5'; newer = service(play)
    async def sdk(messages, **params):
        assert messages[0].content == PROMPTS[old]
        assert params['max_tokens'] == 192
        assert json.loads(messages[1].content)['context']['schema_version'] == 'finale-motivation-context/' + version
        assert 'assessment' not in canonical_json(params['response_format'])
        return output(answer())
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


def test_persistent_exclusive_fact_can_relate_separate_known_events():
    ctx = careful_context('1.5')
    raw = supported(ctx)
    raw['basis'].append({'collection': 'discussion', 'id': 'claim-old'})
    raw['assessment']['facts'].append({'passage_id': 'd0001.p0001', 'excerpt': ctx['discussion'][0]['text']})
    raw['assessment'].update(relation='CONFLICT', event_relation='DIFFERENT',
                             time_relation='PERSISTENT_FACT', identity_relation='SAME', exclusive=True)
    # Only a representability test: a source reviewer must still decide whether
    # the actual facts are persistent, exclusive and about the same identity.
    assert validate_finale_motivation(raw, ctx) == raw
    raw['assessment']['event_relation'] = 'UNKNOWN'
    with pytest.raises(ValueError): validate_finale_motivation(raw, ctx)

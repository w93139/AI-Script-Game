const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { loader, storage } = require('./ts-loader.cjs');

function fixture(phoneBusy = false) {
  return { play_id: 'synthetic-play', selected_character_id: 'a', current_phase: { id: 'investigate-one' },
    characters: [{ id: 'a', name: '甲' }, { id: 'b', name: '乙' }, { id: 'c', name: '丙' }],
    mechanics: { remaining_points: 2, available_actions: [{ id: 'room', label: '花房', cost: 1 }] },
    guided_play: { can_investigate_round: !phoneBusy, can_finish_investigation: !phoneBusy, required_speech_pending: 0 },
    full_game: { call: phoneBusy ? { id: 'call-one', character_ids: ['a', 'c'] } : null, phone_busy: phoneBusy, private_discussion: [] },
    discussion: { entries: [] }, single_player: { available: true, turns: [], topics: [{ id: 'scene', title: '花房见闻',
      responders: [{ character_id: 'b', channels: ['PUBLIC', 'PRIVATE'], intents: [{ id: 'initial', label: '询问见闻', question: '你见到了什么？', available: true }] }] }] } };
}
function components() {
  return loader({ globals: { sessionStorage: storage() }, mocks: {
    '@/stores/playSessionStore': { usePlaySessionStore: select => select({ send() {}, askTopic() {}, busy: false, error: null, unresolved: null }) },
    './AuthorizedImage': { MaterialImages: () => null },
    '@/services/auth': { currentToken: () => 'fixture-user' },
    '@/lib/config': { API_BASE_URL: 'https://speech.invalid' },
  } })('src/components/play/GamePanels.tsx');
}

function failedTurn(overrides = {}) {
  return { id: 'topic-14', topic_id: 'scene', title: '花房见闻', phase_id: 'investigate-one',
    character_id: 'b', channel: 'PUBLIC', question: '你当时看见了什么？', reply_to: 'question-14',
    status: 'FAILED', receipt_status: 'INVALID', can_fallback: true, reply_request: { idempotency_key: 'original-key' }, ...overrides };
}

test('failed answers survive a reload next to the questions with explicit recovery and no retry', () => {
  const { Exchange } = components(); const play = fixture();
  play.single_player.turns = [failedTurn()];
  const html = renderToStaticMarkup(React.createElement(Exchange, { play, locked: false, noteKey: 'scope:play:phase' }));
  assert.match(html, /乙 · 公开回答/);
  assert.match(html, /未通过核验/);
  assert.match(html, /使用资料简答，继续游戏/);
  assert.match(html, /不会再次请求 AI/);
  assert.ok(html.indexOf('使用资料简答，继续游戏') < html.indexOf('陈述我的发现'));
  assert.doesNotMatch(html, /请角色回应|核对原回应/);
});

test('successful public answers display only the authorized reply matching role, phase and question', () => {
  const { Exchange } = components(); const play = fixture();
  play.single_player.turns = [failedTurn({ status: 'OK', can_fallback: false })];
  play.role_responses = { entries: [
    { speaker: 'c', reply_to: 'question-14', phase_id: 'investigate-one', text: '无关角色答案' },
    { speaker: 'b', reply_to: 'question-other', phase_id: 'investigate-one', text: '无关问题答案' },
    { speaker: 'b', reply_to: 'question-14', phase_id: 'investigate-two', text: '无关阶段答案' },
    { speaker: 'b', reply_to: 'question-14', phase_id: 'investigate-one', text: '我看见一只空花盆。' },
  ] };
  const html = renderToStaticMarkup(React.createElement(Exchange, { play, locked: false, noteKey: 'scope:play:phase' }));
  assert.match(html, /我看见一只空花盆/);
  assert.doesNotMatch(html, /无关|使用资料简答/);
});

test('fallback is an explicit saved answer, while unavailable and pending replies cannot start another model call', () => {
  const { Exchange } = components(); const play = fixture();
  play.single_player.turns = [failedTurn({ id: 'fallback', status: 'FALLBACK', can_fallback: false, answer: '我当时在花房。' }),
    failedTurn({ id: 'unavailable', can_fallback: false }),
    failedTurn({ id: 'pending', status: 'PENDING', receipt_status: 'PENDING', can_fallback: false }),
    failedTurn({ id: 'old-phase', phase_id: 'old-phase' })];
  const html = renderToStaticMarkup(React.createElement(Exchange, { play, locked: true, noteKey: 'scope:play:phase' }));
  assert.match(html, /我当时在花房/);
  assert.match(html, /已采用资料简答/);
  assert.match(html, /当前不能使用资料简答/);
  assert.match(html, /核对原回应/);
  assert.doesNotMatch(html, /使用资料简答，继续游戏|请角色回应|data-topic-turn="old-phase"/);
  assert.ok(html.indexOf('data-topic-turn="pending"') < html.indexOf('data-topic-turn="fallback"'));
});

test('active private call explains both disabled investigation and progression, and offers a local exit', () => {
  const { Investigation } = components();
  const html = renderToStaticMarkup(React.createElement(Investigation, { play: fixture(true), locked: false }));
  assert.match(html, /正在与丙单独对话/);
  assert.match(html, /结束对话，恢复调查/);
  assert.match(html, /<fieldset disabled=""/);
  assert.match(html, /id="phase-progress"/);
  assert.match(html, /请先结束单独对话，再继续下一阶段/);
});

test('ending a call enables the actual selection inputs and next-stage action despite unused points', () => {
  const { Investigation } = components();
  const play = fixture(false); play.can_advance = false;
  const html = renderToStaticMarkup(React.createElement(Investigation, { play, locked: false }));
  assert.doesNotMatch(html, /<fieldset disabled=""/);
  assert.match(html, /<input type="checkbox"/);
  assert.match(html, /提前进入下一阶段/);
  assert.doesNotMatch(html, /disabled=""[^>]*>结束本轮调查/);
});

test('a private peer without unlocked questions gets an explanation, not an empty question selector', () => {
  const { Exchange } = components();
  const html = renderToStaticMarkup(React.createElement(Exchange, { play: fixture(true), locked: false, noteKey: 'scope:play:phase' }));
  assert.match(html, /向丙提问/);
  assert.match(html, /对方当前没有可问的问题/);
  assert.doesNotMatch(html, /<option/);
  assert.match(html, /不会自动请求 AI 回答/);
  assert.match(html, /记录单独发言/);
});

test('available questions offer one explicit ask-and-reply action ahead of statement recording', () => {
  const { Exchange } = components();
  const html = renderToStaticMarkup(React.createElement(Exchange, { play: fixture(), locked: false, noteKey: 'scope:play:phase' }));
  assert.match(html, /花房见闻 · 乙 · 询问见闻 · 公开/);
  assert.doesNotMatch(html, /花房见闻 · 乙 · 询问见闻 · 私聊/);
  assert.ok(html.indexOf('发送问题并等待回应') < html.indexOf('陈述我的发现'));
  assert.match(html, /记录公开发言/);
});

test('the repeated-call rule gives an actionable explanation instead of a misleading refresh instruction', () => {
  const axios = { create: () => ({ interceptors: { request: { use() {} } } }), isAxiosError: () => true };
  const { errorCode } = loader({ mocks: { axios, './config': { API_BASE_URL: 'http://127.0.0.1:1' } } })('src/lib/http.ts');
  const message = errorCode({ response: { status: 409, data: { detail: 'FULL_PLAY_CALL_PEER_REPEATED' } } });
  assert.match(message, /先选择其他角色/);
  assert.doesNotMatch(message, /刷新进度/);
  assert.match(errorCode({ response: { status: 409, data: { detail: 'PACKAGE_PLAY_REVISION_CONFLICT' } } }), /刷新进度/);
});

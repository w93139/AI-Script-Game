const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { loader, storage, plain } = require('./ts-loader.cjs');

function playView() {
  return { play_id: 'real-http-play', selected_character_id: 'd', settled: false, pending_ai: false,
    script: { title: '合成接口测试' }, current_phase: { id: 'reading', title: '阅读' },
    characters: [{ id: 'a', name: '甲' }, { id: 'd', name: '丁' }],
    full_game: { phase_kind: 'READING' }, public_knowledge: [], private_knowledge: [],
    public_evidence: [], private_evidence: [], discussion: { entries: [] },
    role_responses: { entries: [] }, dialogue: [], can_advance: true,
    memories: { schema_version: 'package-memory-view/1.0', entries: [] } };
}

test('an empty real discussion remains empty and private messages never become public entries', () => {
  const { publicEntries } = loader()('src/lib/playView.ts');
  const play = playView();
  play.full_game.private_discussion = [{ id: 'private', sequence: 1, speaker: 'a', text: '私人内容' }];
  assert.deepEqual(plain(publicEntries(play)), []);
});

test('public entries merge real statements and replies in sequence without duplicates', () => {
  const { publicEntries } = loader()('src/lib/playView.ts');
  const play = playView();
  play.discussion.entries = [{ id: 'human', sequence: 3, speaker: 'd', text: '本人说法' },
    { id: 'earlier', sequence: 1, speaker: 'a', text: '前一条' }];
  play.role_responses.entries = [{ id: 'reply', sequence: 4, speaker: 'a', text: '真实回应' },
    { id: 'earlier', sequence: 1, speaker: 'a', text: '前一条' }];
  const original = JSON.stringify(play);
  assert.deepEqual(plain(publicEntries(play)), [
    { id: 'earlier', seq: 1, speaker: '甲', self: false, text: '前一条' },
    { id: 'human', seq: 3, speaker: '丁', self: true, text: '本人说法' },
    { id: 'reply', seq: 4, speaker: '甲', self: false, text: '真实回应' },
  ]);
  assert.equal(JSON.stringify(play), original);
});

test('the server phase kind wins over the presence of a mechanics ledger', () => {
  const { phaseKind } = loader()('src/lib/playView.ts');
  const play = playView();
  play.mechanics = { available_actions: [] };
  assert.equal(phaseKind(play), 'READING');
  play.full_game.phase_kind = 'FINALE';
  assert.equal(phaseKind(play), 'FINALE');
});

test('pending server receipts reconstruct the exact original endpoint, key, revision and authorized target', () => {
  const { pendingRequests } = loader()('src/lib/playView.ts');
  const play = playView();
  play.revision = 90;
  play.table_decisions = { requests: [{ status: 'PENDING', request_id: 'original-table-key',
    revision: 14, character_id: 'b', action: 'SEAL_FINALE' }] };
  play.role_responses.requests = [{ status: 'PENDING', request_id: 'original-public-key',
    revision: 28, character_id: 'c', reply_to: 'statement-25' }];
  play.private_replies = { requests: [{ status: 'PENDING', request_id: 'original-private-key',
    revision: 37, character_id: 'e', reply_to: 'private-31' }] };
  const before = JSON.stringify(play);
  assert.deepEqual(plain(pendingRequests(play)), [
    { endpoint: 'decisions', body: { schema_version: 'package-table-decision-command/1.0',
      expected_revision: 14, idempotency_key: 'original-table-key', character_id: 'b', action: 'SEAL_FINALE' } },
    { endpoint: 'responses', body: { schema_version: 'package-dialogue-command/1.0',
      expected_revision: 28, idempotency_key: 'original-public-key', character_id: 'c', reply_to: 'statement-25', action: 'RESPOND' } },
    { endpoint: 'private-responses', body: { schema_version: 'package-private-dialogue-command/1.0',
      expected_revision: 37, idempotency_key: 'original-private-key', character_id: 'e', reply_to: 'private-31', action: 'RESPOND_PRIVATE' } },
  ]);
  assert.equal(JSON.stringify(play), before);
});

test('terminal receipts and absent receipt groups never produce a new pending request', () => {
  const { pendingRequests } = loader()('src/lib/playView.ts');
  const play = playView();
  const statuses = ['OK', 'INVALID', 'UNKNOWN', 'STALE', 'EXPIRED'];
  const receipts = statuses.map((status, i) => ({ status, request_id: 'terminal-' + i,
    revision: i, character_id: 'a', action: 'SEAL_FINALE', reply_to: 'old-statement' }));
  play.table_decisions = { requests: receipts };
  play.role_responses.requests = receipts;
  play.private_replies = { requests: receipts };
  assert.deepEqual(plain(pendingRequests(play)), []);
  assert.deepEqual(plain(pendingRequests({})), []);
});

function materials({ title, items }) {
  return React.createElement('section', null, title,
    items.map(item => React.createElement('p', { key: item.id }, item.text)));
}
function noEffectsReact(stateOverride) {
  let index = 0;
  return { ...React, useEffect: () => {}, useRef: value => ({ current: value }),
    useState: initial => [stateOverride?.[index++] ?? (typeof initial === 'function' ? initial() : initial), () => {}] };
}

test('the real archive reads memories.entries and shows only acquired memory text', () => {
  const play = playView();
  play.memories.entries.push({ id: 'earned-memory', title: '已获回忆', text: '只来自后端已授予回忆的正文' });
  play.private_knowledge.push({ id: 'private-book', text: '角色资料不应冒充回忆' });
  const load = loader({ globals: { localStorage: storage() }, mocks: {
    react: noEffectsReact(['memories']),
    './GamePanels': { Materials: materials, inputClass: '' },
  } });
  const { ArchiveDrawer } = load('src/components/play/ArchiveDrawer.tsx');
  const html = renderToStaticMarkup(React.createElement(ArchiveDrawer, { play, scope: 'account', onClose() {} }));
  assert.match(html, /只来自后端已授予回忆的正文/);
  assert.doesNotMatch(html, /角色资料不应冒充回忆/);
});

test('the real play room does not render sample dialogue when its actual discussion is empty', () => {
  let narrativeCalls = 0;
  const play = playView();
  const state = { mode: 'live', play, opening: null, releases: [], error: null,
    busy: false, unresolved: null, scope: 'account', bootstrap() {}, refresh() {}, send() {}, invalidate() {} };
  const load = loader({ mocks: {
    react: noEffectsReact(),
    'next/link': ({ children }) => React.createElement('a', null, children),
    'next/navigation': { useSearchParams: () => new URLSearchParams('play_id=real-http-play') },
    '@/stores/playSessionStore': { usePlaySessionStore: () => state },
    '@/services/auth': { currentToken: () => 'account' },
    '@/lib/config': { API_BASE_URL: 'http://127.0.0.1:9999' },
    './NarrativeStream': { NarrativeStream: () => { narrativeCalls++; return React.createElement('div', null, 'FAKE_DIALOGUE'); } },
    './ArchiveDrawer': { ArchiveDrawer: () => null },
    './GamePanels': { Materials: materials, Investigation: () => null, Finale: () => null,
      Exchange: () => null, Ending: () => null, buttonClass: '', primaryClass: '', inputClass: '' },
  } });
  const { PlayRoom } = load('src/components/play/PlayRoom.tsx');
  const html = renderToStaticMarkup(React.createElement(PlayRoom));
  assert.equal(narrativeCalls, 0);
  assert.doesNotMatch(html, /FAKE_DIALOGUE|公开交流记录/);
  assert.match(html, /合成接口测试/);
});

test('same-page account event invalidates both the real speech guard and room before old content can stay visible', () => {
  const window = new EventTarget(), localStorage = storage(), effects = [];
  let invalidations = 0;
  const play = playView();
  const state = { mode: 'live', play, opening: null, releases: [], error: null, busy: false,
    unresolved: null, scope: 'old-account', bootstrap() {}, refresh() {}, send() {},
    invalidate() { invalidations++; state.play = null; state.scope = ''; state.mode = 'error'; } };
  const store = () => state; store.getState = () => state;
  const load = loader({ globals: { window, localStorage, Event }, mocks: {
    react: { ...noEffectsReact(), useEffect: callback => effects.push(callback) },
    '@/lib/http': { http: {} },
    'next/link': ({ children }) => React.createElement('a', null, children),
    'next/navigation': { useSearchParams: () => new URLSearchParams('play_id=real-http-play') },
    '@/stores/playSessionStore': { usePlaySessionStore: store },
    '@/lib/config': { API_BASE_URL: 'http://127.0.0.1:9999' },
    './NarrativeStream': { NarrativeStream: () => null },
    './ArchiveDrawer': { ArchiveDrawer: () => null },
    './GamePanels': { Materials: materials, Investigation: () => null, Finale: () => null,
      Exchange: () => null, Ending: () => null, buttonClass: '', primaryClass: '', inputClass: '' },
  } });
  const auth = load('src/services/auth.ts'); auth.saveToken({ access_token: 'old-account' });
  const { PlayRoom } = load('src/components/play/PlayRoom.tsx');
  assert.match(renderToStaticMarkup(PlayRoom()), /合成接口测试/);
  const cleanups = effects.splice(0).map(effect => effect());
  let cancelled = 0;
  const guard = load('src/services/playSpeechAuth.ts').watchPackagePlayAuth(() => cancelled++);
  auth.saveToken({ access_token: 'new-account' });
  assert.equal(invalidations, 1); assert.equal(cancelled, 1); assert.equal(guard.isCurrent(), false);
  assert.equal(state.play, null); assert.equal(state.scope, '');
  assert.doesNotMatch(renderToStaticMarkup(PlayRoom()), /合成接口测试|本人阅读资料/);
  cleanups.forEach(cleanup => cleanup?.()); guard.dispose();
  auth.clearToken();
  assert.equal(invalidations, 1); assert.equal(cancelled, 1);
});

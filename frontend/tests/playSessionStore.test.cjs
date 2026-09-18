const test = require('node:test');
const assert = require('node:assert/strict');
const { loader, storage, deferred, plain } = require('./ts-loader.cjs');

function fixture(id = 'play-a', character = 'a', revision = 0) {
  return { play_id: id, opening_session_id: 'opening-' + character, selected_character_id: character,
    revision, settled: false, last_ai_status: null, pending_ai: false };
}
function harness(options = {}) {
  const sessionStorage = options.storage ?? storage();
  let token = options.token ?? 'account-a';
  let key = 0;
  const calls = [];
  const defaults = {
    getPlay: async id => fixture(id), getSession: async id => ({ session_id: id, release_id: 1,
      selected_character_id: 'd', characters: [{ id: 'a' }, { id: 'd' }] }),
    listReleases: async () => [], findPlay: async () => null,
    createSession: async body => ({ session_id: 'opening-' + body.character_id, release_id: body.release_id,
      selected_character_id: body.character_id }),
    createPlay: async body => ({ ...fixture(), opening_session_id: body.opening_session_id }),
    command: async id => fixture(id, 'a', 1),
  };
  const apis = {};
  for (const [name, fallback] of Object.entries(defaults)) {
    apis[name] = async (...args) => {
      calls.push({ name, args: plain(args), token });
      return (options.api?.[name] ?? fallback)(...args);
    };
  }
  const load = loader({ globals: { sessionStorage }, mocks: {
    '@/services/auth': { ensureSession: async () => {}, currentToken: () => token,
      sessionScope: async () => 'scope-' + token },
    '@/services/play': apis,
    '@/lib/id': { newKey: () => `request-${++key}` },
    '@/lib/http': { errorCode: error => error.message },
    axios: { isAxiosError: error => error?.isAxiosError === true },
  } });
  const store = load('src/stores/playSessionStore.ts').usePlaySessionStore;
  return { store, calls, sessionStorage, setToken: value => { token = value; }, load,
    requests: name => calls.filter(call => call.name === name) };
}

test('advance and settle dispatch omit target, including null, and carry the current revision', async () => {
  const h = harness();
  const { actionPayload } = h.load('src/lib/playView.ts');
  await h.store.getState().bootstrap({ playId: 'original-play' });
  for (const action of ['ADVANCE_PHASE', 'SETTLE']) {
    assert.equal(await h.store.getState().send('actions', actionPayload(action)), true);
    const call = h.requests('command').at(-1);
    assert.equal(call.args[0], 'original-play');
    assert.equal(call.args[1], 'actions');
    assert.equal(call.args[2].action, action);
    assert.equal(Object.hasOwn(call.args[2], 'target'), false);
    assert.equal(call.args[2].expected_revision, action === 'ADVANCE_PHASE' ? 0 : 1);
  }
});

test('uncertain response persists the original request across refresh and permits only explicit same-key checking', async () => {
  const disk = storage();
  const first = harness({ storage: disk, api: { command: async () => { throw new Error('network-timeout'); } } });
  await first.store.getState().bootstrap({ playId: 'original-play' });
  assert.equal(await first.store.getState().send('actions', { action: 'ADVANCE_PHASE' }), false);
  const body = first.requests('command')[0].args[2];
  assert.equal(first.store.getState().unresolved.body.idempotency_key, body.idempotency_key);
  assert.equal(await first.store.getState().send('actions', { action: 'SETTLE' }), false);
  assert.equal(first.requests('command').length, 1);
  const restored = harness({ storage: disk });
  await restored.store.getState().bootstrap({ playId: 'original-play' });
  assert.equal(restored.requests('command').length, 0, 'restoring must not auto-retry');
  assert.deepEqual(plain(restored.store.getState().unresolved.body), body);
  assert.equal(await restored.store.getState().checkRequest(), true);
  assert.deepEqual(restored.requests('command')[0].args[2], body);
  assert.equal(restored.store.getState().unresolved, null);
  assert.equal([...disk.values.keys()].some(key => key.startsWith('play-attempt:')), false);
});

test('double-click sends one request and stores it before dispatch', async () => {
  const pending = deferred();
  const disk = storage();
  const h = harness({ storage: disk, api: { command: async () => {
    assert.equal([...disk.values.keys()].filter(key => key.startsWith('play-attempt:')).length, 1);
    return pending.promise;
  } } });
  await h.store.getState().bootstrap({ playId: 'original-play' });
  const first = h.store.getState().send('actions', { action: 'ADVANCE_PHASE' });
  const second = h.store.getState().send('actions', { action: 'ADVANCE_PHASE' });
  assert.equal(h.requests('command').length, 1);
  assert.equal(await second, false);
  pending.resolve(fixture('original-play', 'a', 1));
  assert.equal(await first, true);
});

test('HTTP 200 with pending_ai keeps the original receipt across reload until a terminal same-key check', async () => {
  const disk = storage();
  const first = harness({ storage: disk, api: { command: async id => ({
    ...fixture(id, 'a', 1), pending_ai: true,
  }) } });
  await first.store.getState().bootstrap({ playId: 'waiting-play' });
  const frozen = { schema_version: 'package-dialogue-command/1.0', action: 'RESPOND',
    expected_revision: 0, idempotency_key: 'server-frozen-key', character_id: 'b', reply_to: 'statement-1' };
  assert.equal(await first.store.getState().send('responses', {}, frozen), false);
  assert.deepEqual(plain(first.store.getState().unresolved.body), frozen);
  assert.equal(first.store.getState().play.pending_ai, true);
  assert.equal(await first.store.getState().send('actions', { action: 'ADVANCE_PHASE' }), false);
  const stillPending = harness({ storage: disk, api: {
    getPlay: async id => ({ ...fixture(id, 'a', 1), pending_ai: true }),
    command: async id => ({ ...fixture(id, 'a', 1), pending_ai: true }),
  } });
  await stillPending.store.getState().bootstrap({ playId: 'waiting-play' });
  assert.equal(await stillPending.store.getState().checkRequest(), false);
  assert.deepEqual(stillPending.requests('command')[0].args[2], frozen);
  assert.deepEqual(plain(stillPending.store.getState().unresolved.body), frozen);
  const completed = harness({ storage: disk, api: {
    getPlay: async id => ({ ...fixture(id, 'a', 1), pending_ai: true }),
    command: async id => ({ ...fixture(id, 'a', 2), last_ai_status: 'OK' }),
  } });
  await completed.store.getState().bootstrap({ playId: 'waiting-play' });
  assert.equal(await completed.store.getState().checkRequest(), true);
  assert.deepEqual(completed.requests('command')[0].args[2], frozen);
  assert.equal(completed.store.getState().unresolved, null);
  assert.equal(completed.store.getState().play.pending_ai, false);
  assert.equal([...disk.values.keys()].some(key => key.startsWith('play-attempt:')), false);
});

test('unavailable session storage prevents dispatch rather than losing the recovery key', async () => {
  const disk = storage();
  disk.setItem = () => { throw new Error('storage-full'); };
  const h = harness({ storage: disk });
  await h.store.getState().bootstrap({ playId: 'original-play' });
  assert.equal(await h.store.getState().send('actions', { action: 'ADVANCE_PHASE' }), false);
  assert.equal(h.requests('command').length, 0);
  assert.equal(h.store.getState().busy, false);
});

test('resume by play ID only reads that play and never creates or selects a new one', async () => {
  const h = harness();
  await h.store.getState().bootstrap({ playId: 'saved-play' });
  assert.deepEqual(h.calls.map(call => call.name), ['getPlay']);
  assert.equal(h.store.getState().play.play_id, 'saved-play');
  assert.equal(h.store.getState().mode, 'live');
});

test('resume by opening ID preserves its role and reuses an existing play', async () => {
  const h = harness({ api: { findPlay: async () => fixture('saved-play', 'd') } });
  await h.store.getState().bootstrap({ openingSessionId: 'saved-opening' });
  assert.equal(h.store.getState().opening.selected_character_id, 'd');
  assert.equal(h.store.getState().mode, 'opening');
  await h.store.getState().begin();
  assert.deepEqual(h.calls.map(call => call.name), ['getSession', 'findPlay']);
  assert.equal(h.store.getState().play.selected_character_id, 'd');
});

test('preview respects the explicit selected role and uses a stable creation key after an uncertain response', async () => {
  let attempts = 0;
  const h = harness({ api: { createSession: async body => {
    if (!attempts++) throw new Error('timeout');
    return { session_id: 'selected-opening', selected_character_id: body.character_id };
  } } });
  await h.store.getState().bootstrap();
  await h.store.getState().preview(9, 'e');
  await h.store.getState().preview(9, 'e');
  const [first, second] = h.requests('createSession');
  assert.deepEqual(first.args, second.args);
  assert.equal(second.args[0].character_id, 'e');
  assert.equal(h.store.getState().opening.selected_character_id, 'e');
});

test('old identity late response cannot overwrite a newly restored play or its busy state', async () => {
  const pending = deferred();
  const h = harness({ api: { command: async () => pending.promise } });
  await h.store.getState().bootstrap({ playId: 'old-play' });
  const sent = h.store.getState().send('actions', { action: 'ADVANCE_PHASE' });
  h.setToken('account-b');
  h.store.getState().invalidate();
  await h.store.getState().bootstrap({ playId: 'new-play' });
  pending.resolve(fixture('old-play', 'a', 99));
  assert.equal(await sent, false);
  assert.equal(h.store.getState().play.play_id, 'new-play');
  assert.equal(h.store.getState().play.revision, 0);
  assert.equal(h.store.getState().unresolved, null);
  assert.equal(h.store.getState().busy, false);
  assert.equal([...h.sessionStorage.values.keys()].some(key => key.includes('scope-account-a:old-play')), true);
});

test('a late bootstrap response cannot restore private data after identity invalidation', async () => {
  const pending = deferred();
  const entered = deferred();
  const h = harness({ api: { getPlay: async () => { entered.resolve(); return pending.promise; } } });
  const restoring = h.store.getState().bootstrap({ playId: 'old-private-play' });
  await entered.promise;
  assert.equal(h.requests('getPlay').length, 1);
  h.setToken('account-b');
  h.store.getState().invalidate();
  pending.resolve(fixture('old-private-play', 'd'));
  await restoring;
  assert.equal(h.store.getState().play, null);
  assert.equal(h.store.getState().opening, null);
  assert.equal(h.store.getState().mode, 'error');
});

test('a pending request is scoped by both account and play', async () => {
  const disk = storage();
  const first = harness({ storage: disk, api: { command: async () => { throw new Error('timeout'); } } });
  await first.store.getState().bootstrap({ playId: 'same-id' });
  await first.store.getState().send('actions', { action: 'ADVANCE_PHASE' });
  const otherAccount = harness({ storage: disk, token: 'account-b' });
  await otherAccount.store.getState().bootstrap({ playId: 'same-id' });
  assert.equal(otherAccount.store.getState().unresolved, null);
  const otherPlay = harness({ storage: disk });
  await otherPlay.store.getState().bootstrap({ playId: 'different-id' });
  assert.equal(otherPlay.store.getState().unresolved, null);
});

for (const operation of ['send', 'refresh', 'preview', 'begin']) {
  test(`same-tab identity replacement blocks ${operation} before network activity without waiting for a browser event`, async () => {
    const h = harness();
    if (operation === 'begin') await h.store.getState().bootstrap({ openingSessionId: 'owned-opening' });
    else await h.store.getState().bootstrap({ playId: 'owned-play' });
    const count = h.calls.length;
    h.setToken('account-b'); // no storage/focus event and no explicit invalidate()
    if (operation === 'send') await h.store.getState().send('actions', { action: 'ADVANCE_PHASE' });
    else if (operation === 'preview') await h.store.getState().preview(1, 'e');
    else await h.store.getState()[operation]();
    assert.equal(h.calls.length, count);
    assert.equal(h.store.getState().play, null);
    assert.equal(h.store.getState().opening, null);
    assert.equal(h.store.getState().mode, 'error');
  });
}

for (const operation of ['refresh', 'begin', 'preview']) {
  test(`same-tab identity replacement during a late failed ${operation} clears the previous private view`, async () => {
    const pending = deferred();
    let reads = 0;
    const h = harness({ api: { getPlay: async id => ++reads === 1 ? fixture(id) : pending.promise,
      findPlay: async () => pending.promise, createSession: async () => pending.promise } });
    if (operation === 'refresh') await h.store.getState().bootstrap({ playId: 'private-old-play' });
    else await h.store.getState().bootstrap({ openingSessionId: 'private-old-opening' });
    const inFlight = operation === 'preview' ? h.store.getState().preview(1, 'e') : h.store.getState()[operation]();
    h.setToken('account-b');
    pending.reject(new Error('network-timeout'));
    await inFlight;
    assert.equal(h.store.getState().play, null);
    assert.equal(h.store.getState().opening, null);
    assert.equal(h.store.getState().mode, 'error');
  });
}

test('identity replacement during failed conflict recovery also clears the previous private view', async () => {
  const pending = deferred();
  const entered = deferred();
  let reads = 0;
  const h = harness({ api: {
    getPlay: async id => {
      if (++reads === 1) return fixture(id);
      entered.resolve(); return pending.promise;
    },
    command: async () => {
      const error = new Error('REVISION_CONFLICT');
      error.isAxiosError = true; error.response = { status: 409 }; throw error;
    },
  } });
  await h.store.getState().bootstrap({ playId: 'private-old-play' });
  const sending = h.store.getState().send('actions', { action: 'ADVANCE_PHASE' });
  await entered.promise;
  h.setToken('account-b');
  pending.reject(new Error('recovery-timeout'));
  assert.equal(await sending, false);
  assert.equal(h.store.getState().play, null);
  assert.equal(h.store.getState().mode, 'error');
});

test('late findPlay result after identity change must not create a play under the new identity', async () => {
  const pending = deferred();
  const h = harness({ api: { findPlay: async () => pending.promise } });
  await h.store.getState().bootstrap({ openingSessionId: 'old-opening' });
  const beginning = h.store.getState().begin();
  h.setToken('account-b');
  h.store.getState().invalidate();
  pending.resolve(null);
  await beginning;
  assert.equal(h.requests('createPlay').length, 0);
  assert.equal(h.store.getState().play, null);
});

test('server rejection clears uncertainty and refreshes the authorized progress', async () => {
  const h = harness({ api: { command: async () => {
    const error = new Error('REVISION_CONFLICT');
    error.isAxiosError = true; error.response = { status: 409 }; throw error;
  } } });
  await h.store.getState().bootstrap({ playId: 'saved-play' });
  assert.equal(await h.store.getState().send('actions', { action: 'ADVANCE_PHASE' }), false);
  assert.equal(h.store.getState().unresolved, null);
  assert.equal(h.requests('getPlay').length, 2);
  assert.equal(h.store.getState().error, 'REVISION_CONFLICT');
});

const topicChoice = { topic_id: 'scene', character_id: 'b', intent_id: 'initial', channel: 'PUBLIC' };

test('a historical invalid answer does not turn a successful fallback or later investigation into another error', async () => {
  const h = harness({ api: { getPlay: async id => ({ ...fixture(id), last_ai_status: 'INVALID' }),
    command: async id => ({ ...fixture(id, 'a', 4), last_ai_status: 'INVALID' }) } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  await h.store.getState().send('topic', { action: 'USE_FALLBACK', payload: { turn_id: 'topic-1' } });
  assert.equal(h.store.getState().error, null);
  await h.store.getState().send('guided', { action: 'INVESTIGATE_ROUND' });
  assert.equal(h.store.getState().error, null);
  await h.store.getState().send('phone-pause', { action: 'PAUSE_PHONE' });
  assert.equal(h.store.getState().error, null);
  assert.deepEqual(h.requests('command').map(c => c.args[1]), ['topic', 'guided', 'phone-pause']);
});

test('a finite-question failure uses its durable recovery card and never retries or adopts a fallback automatically', async () => {
  const h = harness({ api: { getPlay: async id => topicPlay(id), command: async (id, endpoint, body) =>
    endpoint === 'topic' ? savedTopic(id, body) : topicPlay(id, { revision: 3, last_ai_status: 'INVALID',
      single_player: { turns: [{ phase_id: 'investigate-one', status: 'FAILED', can_fallback: true,
        reply_request: { idempotency_key: body.idempotency_key } }] } }) } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  await h.store.getState().askTopic(topicChoice);
  assert.equal(h.store.getState().error, null);
  assert.equal(h.store.getState().unresolved, null);
  assert.equal(h.store.getState().play.single_player.turns[0].status, 'FAILED');
  assert.deepEqual(h.requests('command').map(c => c.args[1]), ['topic', 'responses']);
});

test('a model failure without a finite-question recovery card still reports an error', async () => {
  const h = harness({ api: { command: async id => ({ ...fixture(id, 'a', 2), last_ai_status: 'INVALID' }) } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  await h.store.getState().send('responses', { action: 'RESPOND' });
  assert.match(h.store.getState().error, /回应未成功/);
});
function topicPlay(id = 'play-a', overrides = {}) {
  return { ...fixture(id), current_phase: { id: 'investigate-one' },
    full_game: { call: null, phone_busy: false },
    single_player: { available: true, turns: [], last_command: null }, ...overrides };
}
function savedTopic(id, body, changes = {}) {
  const seq = body.expected_revision + 1;
  const reply = { schema_version: body.payload.channel === 'PRIVATE' ? 'package-private-dialogue-command/1.0' : 'package-dialogue-command/1.0',
    action: body.payload.channel === 'PRIVATE' ? 'RESPOND_PRIVATE' : 'RESPOND',
    expected_revision: seq, idempotency_key: 'server-frozen-reply', character_id: body.payload.character_id, reply_to: 'saved-question' };
  return topicPlay(id, { revision: seq, single_player: { available: true,
    last_command: { action: 'ASK_TOPIC', idempotency_key: body.idempotency_key, sequence: seq },
    turns: [{ id: 'topic-' + seq, ...body.payload, phase_id: 'investigate-one', status: 'READY', can_fallback: false,
      reply_request: reply, ...changes }] } });
}

test('one explicit question click saves then sends exactly the server-frozen public reply', async () => {
  const h = harness({ api: { getPlay: async id => topicPlay(id), command: async (id, endpoint, body) =>
    endpoint === 'topic' ? savedTopic(id, body) : topicPlay(id, { revision: 3, last_ai_status: 'OK' }) } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  assert.equal(await h.store.getState().askTopic(topicChoice), true);
  const calls = h.requests('command');
  assert.deepEqual(calls.map(c => c.args[1]), ['topic', 'responses']);
  assert.deepEqual(calls[1].args[2], savedTopic('play-a', calls[0].args[2]).single_player.turns[0].reply_request);
  await h.store.getState().refresh();
  assert.equal(h.requests('command').length, 2, 'refresh never starts another answer');
});

test('private question stays on the same call and uses the private response endpoint', async () => {
  const call = { id: 'same-call', character_ids: ['a', 'b'] };
  const h = harness({ api: { getPlay: async id => topicPlay(id, { full_game: { call, phone_busy: true } }),
    command: async (id, endpoint, body) => endpoint === 'topic'
      ? { ...savedTopic(id, body), full_game: { call, phone_busy: true } } : topicPlay(id, { revision: 3 }) } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  await h.store.getState().askTopic({ ...topicChoice, channel: 'PRIVATE' });
  assert.deepEqual(h.requests('command').map(c => c.args[1]), ['topic', 'private-responses']);
  assert.equal(h.requests('command')[1].args[2].action, 'RESPOND_PRIVATE');
});

test('double-clicking a question does not save or charge a second request', async () => {
  const pending = deferred(); let question;
  const h = harness({ api: { getPlay: async id => topicPlay(id), command: async (id, endpoint, body) => {
    if (endpoint === 'topic') { question = body; return pending.promise; }
    return topicPlay(id, { revision: 3 });
  } } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  const first = h.store.getState().askTopic(topicChoice);
  assert.equal(await h.store.getState().askTopic(topicChoice), false);
  pending.resolve(savedTopic('play-a', question));
  await first;
  assert.deepEqual(h.requests('command').map(c => c.args[1]), ['topic', 'responses']);
});

test('an uncertain question save is recovered without automatically starting an answer', async () => {
  const h = harness({ api: { getPlay: async id => topicPlay(id), command: async () => { throw new Error('timeout'); } } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  assert.equal(await h.store.getState().askTopic(topicChoice), false);
  assert.equal(h.requests('command').length, 1);
  assert.equal(h.store.getState().unresolved.endpoint, 'topic');
});

test('unavailable AI and stale READY questions keep explicit recovery instead of starting a paid reply', async () => {
  for (const changes of [{ can_fallback: true }, { reply_request: null }, { status: 'FAILED' },
    { reply_request: { expected_revision: 100, idempotency_key: 'stale-key' } }]) {
    const h = harness({ api: { getPlay: async id => topicPlay(id), command: async (id, endpoint, body) => savedTopic(id, body, changes) } });
    await h.store.getState().bootstrap({ playId: 'play-a' });
    await h.store.getState().askTopic(topicChoice);
    assert.equal(h.requests('command').length, 1);
  }
});

test('identity or route replacement during question save cannot start a late answer', async () => {
  for (const changeIdentity of [true, false]) {
    const pending = deferred(); let question;
    const h = harness({ api: { getPlay: async id => topicPlay(id), command: async (id, endpoint, body) => { question = body; return pending.promise; } } });
    await h.store.getState().bootstrap({ playId: 'play-a' });
    const operation = h.store.getState().askTopic(topicChoice);
    if (changeIdentity) { h.setToken('account-b'); h.store.getState().invalidate(); }
    await h.store.getState().bootstrap({ playId: 'another-play' });
    pending.resolve(savedTopic('play-a', question));
    assert.equal(await operation, false);
    assert.equal(h.requests('command').length, 1);
    assert.equal(h.store.getState().play.play_id, 'another-play');
  }
});

test('changed call, phase or mismatched save receipt cannot start an answer', async () => {
  for (const change of ['call', 'phase', 'receipt', 'target']) {
    const call = { id: 'original-call', character_ids: ['a', 'b'] };
    const h = harness({ api: { getPlay: async id => topicPlay(id, { full_game: { call, phone_busy: true } }),
      command: async (id, endpoint, body) => {
        const p = { ...savedTopic(id, body), full_game: { call, phone_busy: true } };
        if (change === 'call') p.full_game.call = { ...call, id: 'different-call' };
        if (change === 'phase') p.current_phase.id = 'investigate-two';
        if (change === 'receipt') p.single_player.last_command.idempotency_key = 'another-save';
        if (change === 'target') p.single_player.turns[0].character_id = 'c';
        return p;
      } } });
    await h.store.getState().bootstrap({ playId: 'play-a' });
    await h.store.getState().askTopic({ ...topicChoice, channel: 'PRIVATE' });
    assert.equal(h.requests('command').length, 1, change);
  }
});

test('uncertain reply keeps its frozen key, and no refresh or new question silently retries', async () => {
  const h = harness({ api: { getPlay: async id => topicPlay(id), command: async (id, endpoint, body) => {
    if (endpoint === 'topic') return savedTopic(id, body);
    throw new Error('reply timeout');
  } } });
  await h.store.getState().bootstrap({ playId: 'play-a' });
  assert.equal(await h.store.getState().askTopic(topicChoice), false);
  assert.equal(h.store.getState().unresolved.body.idempotency_key, 'server-frozen-reply');
  await h.store.getState().refresh();
  assert.equal(await h.store.getState().askTopic(topicChoice), false);
  assert.equal(h.requests('command').length, 2);
});

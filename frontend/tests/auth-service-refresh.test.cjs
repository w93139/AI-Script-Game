// 访问令牌静默续期的回归测试（迭代方案第 04 条）。
//
// 令牌有效期由 30 天收敛到 2 小时后，前端必须能用续期凭条在后台换发新令牌，
// 否则使用者每两小时就会被踢回登录页。这里验证换发成功时请求自动重试、
// 换发失败时才真正退出登录，以及并发 401 只换发一次。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');

function compile(relative) {
  const filename = path.join(__dirname, relative);
  return ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    fileName: filename, compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
}

const helper = { exports: {} };
new Function('module', 'exports', compile('../src/lib/authReturnPath.ts'))(helper, helper.exports);

// handlers: (url, options, callIndex) => { ok, status, body }
function session(tokens, handler) {
  let current = new URL('/play/package-play', 'https://app.invalid');
  const location = {
    get href() { return current.href; },
    set href(value) { current = new URL(value, current); },
    replace(value) { current = new URL(value, current); },
    get pathname() { return current.pathname; },
    get search() { return current.search; },
    get hash() { return current.hash; },
  };
  const window = { location, dispatchEvent: () => {} };
  const store = new Map(Object.entries(tokens));
  const storage = {
    getItem: key => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, value),
    removeItem: key => store.delete(key),
  };
  const calls = [];
  const compiled = { exports: {} };
  new Function('require', 'module', 'exports', 'window', 'localStorage', 'fetch', compile('../src/services/authService.ts'))(
    name => {
      if (name === '@/stores/configStore') return { config: { api: { baseUrl: 'https://fixture.invalid' } } };
      if (name === '@/lib/authReturnPath') return helper.exports;
      return require(name);
    },
    compiled, compiled.exports, window, storage,
    async (url, options) => {
      calls.push(url);
      const result = handler(url, options, calls.length - 1);
      return { ok: result.ok, status: result.status, json: async () => result.body };
    },
  );
  return { service: compiled.exports.default, window, store, calls };
}

test('过期的访问令牌会被静默换发，原请求自动重试成功', async () => {
  const fixture = session(
    { access_token: 'stale-token', refresh_token: 'valid-refresh' },
    (url, _options, index) => {
      if (url.endsWith('/api/auth/refresh')) {
        return { ok: true, status: 200, body: { access_token: 'fresh-token', refresh_token: 'next-refresh' } };
      }
      // 第一次带旧令牌失败，换发之后重试成功。
      return index === 0
        ? { ok: false, status: 401, body: { detail: 'expired' } }
        : { ok: true, status: 200, body: { id: 1, username: 'someone' } };
    },
  );

  const user = await fixture.service.getCurrentUser();

  assert.equal(user.username, 'someone');
  assert.deepEqual(fixture.calls.map(url => new URL(url).pathname),
    ['/api/auth/me', '/api/auth/refresh', '/api/auth/me']);
  assert.equal(fixture.store.get('access_token'), 'fresh-token');
  assert.equal(fixture.store.get('refresh_token'), 'next-refresh');
  // 换发成功就不该把人踢去登录页。
  assert.equal(fixture.window.location.pathname, '/play/package-play');
});

test('换发也失败时才退出登录，并保留原页面以便登录后返回', async () => {
  const fixture = session(
    { access_token: 'stale-token', refresh_token: 'revoked-refresh' },
    url => (url.endsWith('/api/auth/refresh')
      ? { ok: false, status: 401, body: { detail: 'revoked' } }
      : { ok: false, status: 401, body: { detail: 'expired' } }),
  );

  await assert.rejects(fixture.service.getCurrentUser());

  assert.equal(fixture.store.has('access_token'), false);
  assert.equal(fixture.store.has('refresh_token'), false);
  assert.equal(fixture.window.location.pathname, '/auth/login');
  assert.match(fixture.window.location.href, /returnUrl=/);
});

test('没有续期凭条时不做多余的换发尝试', async () => {
  const fixture = session(
    { access_token: 'stale-token' },
    () => ({ ok: false, status: 401, body: { detail: 'expired' } }),
  );

  await assert.rejects(fixture.service.getCurrentUser());

  assert.deepEqual(fixture.calls.map(url => new URL(url).pathname), ['/api/auth/me']);
  assert.equal(fixture.window.location.pathname, '/auth/login');
});

test('并发的多个 401 只换发一次凭条', async () => {
  const fixture = session(
    { access_token: 'stale-token', refresh_token: 'valid-refresh' },
    (url, _options, index) => {
      if (url.endsWith('/api/auth/refresh')) {
        return { ok: true, status: 200, body: { access_token: 'fresh-token', refresh_token: 'next-refresh' } };
      }
      // 前三次是并发发出的旧令牌请求，之后的重试都成功。
      return index < 3
        ? { ok: false, status: 401, body: { detail: 'expired' } }
        : { ok: true, status: 200, body: { id: 1, username: 'someone' } };
    },
  );

  const results = await Promise.all([
    fixture.service.getCurrentUser(),
    fixture.service.getCurrentUser(),
    fixture.service.getCurrentUser(),
  ]);

  assert.equal(results.length, 3);
  const refreshCalls = fixture.calls.filter(url => url.endsWith('/api/auth/refresh'));
  assert.equal(refreshCalls.length, 1, '服务端凭条是一次性的，并发换发会互相作废');
});

test('续期请求本身返回 401 时不会再触发一次换发', async () => {
  const fixture = session(
    { access_token: 'stale-token', refresh_token: 'revoked-refresh' },
    () => ({ ok: false, status: 401, body: { detail: 'revoked' } }),
  );

  await assert.rejects(fixture.service.getCurrentUser());

  const refreshCalls = fixture.calls.filter(url => url.endsWith('/api/auth/refresh'));
  assert.equal(refreshCalls.length, 1);
});

test('登出会同时清掉访问令牌和续期凭条', async () => {
  const fixture = session(
    { access_token: 'live-token', refresh_token: 'live-refresh' },
    () => ({ ok: true, status: 200, body: { message: '登出成功', token_revoked: true } }),
  );

  await fixture.service.logout();

  assert.equal(fixture.store.has('access_token'), false);
  assert.equal(fixture.store.has('refresh_token'), false);
});

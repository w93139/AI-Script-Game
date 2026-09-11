// 访客模式探测的回归测试。
//
// 开发期后端打开 ALLOW_ANONYMOUS_ACCESS 后，受保护页面应自动以访客身份进入；
// 后端关着时（生产环境的启动自检会强制关闭）必须原样回到登录页。
// 这里锁定的是"是否开启由后端说了算""被拒绝后不再反复请求""并发只探测一次"。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');

function load() {
  const filename = path.join(__dirname, '../src/lib/guestAccess.ts');
  const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    fileName: filename, compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;

  const store = new Map();
  const sessionStorage = {
    getItem: key => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: key => store.delete(key),
  };
  const compiled = { exports: {} };
  new Function('module', 'exports', 'window', source)(compiled, compiled.exports, { sessionStorage });
  return { api: compiled.exports, store };
}

test('后端开启访客模式时自动进入，无需登录', async () => {
  const { api, store } = load();
  let calls = 0;

  const signedIn = await api.ensureGuestSession(async () => { calls += 1; });

  assert.equal(signedIn, true);
  assert.equal(calls, 1);
  assert.equal(store.has(api.GUEST_PROBE_KEY), false, '成功时不应记为不可用');
});

test('后端关闭访客模式时返回 false，由调用方跳转登录页', async () => {
  const { api, store } = load();

  const signedIn = await api.ensureGuestSession(async () => {
    throw new Error('匿名访问未启用，请先注册账号');
  });

  assert.equal(signedIn, false);
  assert.equal(store.get(api.GUEST_PROBE_KEY), '1');
});

test('被拒绝后本次会话内不再重复请求后端', async () => {
  const { api } = load();
  let calls = 0;
  const reject = async () => { calls += 1; throw new Error('匿名访问未启用'); };

  assert.equal(await api.ensureGuestSession(reject), false);
  assert.equal(await api.ensureGuestSession(reject), false);
  assert.equal(await api.ensureGuestSession(reject), false);

  assert.equal(calls, 1, '每打开一个受保护页面都重试一次是多余的');
});

test('多个受保护组件同时挂载时只探测一次', async () => {
  const { api } = load();
  let calls = 0;
  let release;
  const pending = new Promise(resolve => { release = resolve; });

  const slowSignIn = async () => { calls += 1; await pending; };
  const results = Promise.all([
    api.ensureGuestSession(slowSignIn),
    api.ensureGuestSession(slowSignIn),
    api.ensureGuestSession(slowSignIn),
  ]);
  release();

  assert.deepEqual(await results, [true, true, true]);
  assert.equal(calls, 1);
});

test('登出后重新探测，后端开关改动能被立即反映', async () => {
  const { api } = load();
  let enabled = false;
  let calls = 0;
  const signIn = async () => {
    calls += 1;
    if (!enabled) throw new Error('匿名访问未启用');
  };

  assert.equal(await api.ensureGuestSession(signIn), false);
  enabled = true;
  // 未清除缓存时仍然记着上次的结论。
  assert.equal(await api.ensureGuestSession(signIn), false);
  assert.equal(calls, 1);

  api.clearGuestAccessProbe();

  assert.equal(await api.ensureGuestSession(signIn), true);
  assert.equal(calls, 2);
});

test('会话存储不可用时不影响功能，只是每次多问一遍', async () => {
  const filename = path.join(__dirname, '../src/lib/guestAccess.ts');
  const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    fileName: filename, compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const compiled = { exports: {} };
  // 无痕模式下访问 sessionStorage 会直接抛错。
  const hostile = { get sessionStorage() { throw new Error('storage disabled'); } };
  new Function('module', 'exports', 'window', source)(compiled, compiled.exports, hostile);

  const api = compiled.exports;
  assert.equal(api.guestAccessKnownUnavailable(), false);
  assert.doesNotThrow(() => api.markGuestAccessUnavailable());
  assert.equal(await api.ensureGuestSession(async () => {}), true);
});

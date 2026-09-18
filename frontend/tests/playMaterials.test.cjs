const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { webcrypto } = require('node:crypto');
const { loader, deferred } = require('./ts-loader.cjs');

test('reading Markdown renders headings, emphasis, quotes and Chinese numbered items after OCR layout repair', () => {
  const { PlayText, normalizePlayText } = loader()('src/components/play/PlayText.tsx');
  const source = '# 合成阅读\n\n你在门边\n\n看见 **蓝色纸条**。\n\n你的目的\n1、核对纸条\n2、保留疑问\n\n> 尚不能确定\n\n`代号`和*猜测*';
  const html = renderToStaticMarkup(React.createElement(PlayText, { text: source }));
  assert.match(html, /<h3[^>]*>合成阅读<\/h3>/);
  assert.match(html, /你在门边看见 <strong[^>]*>蓝色纸条<\/strong>。/);
  assert.match(html, /<h3[^>]*>你的目的<\/h3>/);
  assert.match(html, /1、<\/span>核对纸条/);
  assert.match(html, /2、<\/span>保留疑问/);
  assert.match(html, /<blockquote/);
  assert.match(html, /<code[^>]*>代号<\/code>/);
  assert.match(html, /<em>猜测<\/em>/);
  assert.equal(normalizePlayText('第一句话。\n\n第二句话。'), '第一句话。\n\n第二句话。');
  assert.match(source, /门边\n\n看见/, 'presentation must not mutate the original input');
});

test('untrusted HTML and Markdown image/link syntax cannot fetch assets or create active HTML', () => {
  const { PlayText } = loader()('src/components/play/PlayText.tsx');
  const text = '<script>alert(1)</script>\n\n<img src="https://example.invalid/private" onerror="alert(1)">\n\n![remote](https://example.invalid/image)\n\n[x](javascript:alert(1))';
  const html = renderToStaticMarkup(React.createElement(PlayText, { text }));
  assert.doesNotMatch(html, /<script|<img|<a\b/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /!\[remote\]/);
});

test('ending metadata is hidden without deleting or merging the adjacent story and title', () => {
  const { PlayText, normalizePlayText } = loader()('src/components/play/PlayText.tsx');
  const source = '结局四\n〔编辑修订条件〕合成内部选择条件。\n\n你回到庭院，\n打开那封信。\n\n信中提到〔编辑修订条件〕只是一个奇怪称呼。';
  const rendered = renderToStaticMarkup(React.createElement(PlayText, { text: source }));
  assert.match(rendered, /<h3[^>]*>结局四<\/h3>/);
  assert.doesNotMatch(rendered, /合成内部选择条件/);
  assert.match(rendered, /你回到庭院，打开那封信。/);
  assert.match(rendered, /信中提到〔编辑修订条件〕只是一个奇怪称呼。/);
  assert.match(source, /〔编辑修订条件〕合成内部选择条件。/);
  assert.equal(normalizePlayText('```\n〔编辑修订条件〕合成代码。\n```'), '```\n〔编辑修订条件〕合成代码。\n```');
});

test('OCR continuation stays inside one numbered or unordered list item', () => {
  const { PlayText, normalizePlayText } = loader()('src/components/play/PlayText.tsx');
  for (const [first, next] of [['1、', '2、'], ['1. ', '2. '], ['1) ', '2) '], ['- ', '- '], ['* ', '* '], ['+ ', '+ ']]) {
    const source = `${first}他是客座教\n授，住在附\n近。\n${next}下一项。`;
    assert.equal(normalizePlayText(source), `${first}他是客座教授，住在附近。\n${next}下一项。`);
    const html = renderToStaticMarkup(React.createElement(PlayText, { text: source }));
    assert.match(html, /<\/span>他是客座教授，住在附近。<\/p>/);
    assert.equal((html.match(/<p\b/g) || []).length, 2);
    assert.match(source, /教\n授/, 'original source remains unchanged');
  }
});

test('list OCR repair preserves the next block, explicit paragraph gap and terminal punctuation', () => {
  const { normalizePlayText } = loader()('src/components/play/PlayText.tsx');
  for (const boundary of ['2、下一项', '- 下一项', '# 新标题', '你的目的', '> 引用说明', '>引用说明', '```\n合成代码\n```']) {
    const source = `1、尚待核对\n${boundary}`;
    assert.equal(normalizePlayText(source), source);
  }
  for (const punctuation of ['。', '！', '？', '：', '；', '。”']) {
    const source = `1、这一项结束${punctuation}\n下一段说明。`;
    assert.equal(normalizePlayText(source), source);
  }
  assert.equal(normalizePlayText('1、尚待核对\n\n另起一段。'), '1、尚待核对\n\n另起一段。');
});

test('fenced text retains whitespace and Chinese prose instead of OCR joining it', () => {
  const { PlayText } = loader()('src/components/play/PlayText.tsx');
  const html = renderToStaticMarkup(React.createElement(PlayText, { text: '```\n  第一行\n\n  第二行\n```\n\n正常正文。' }));
  assert.match(html, /<code>  第一行\n\n  第二行<\/code>/);
  assert.match(html, /正常正文。/);
});

test('authorized visual rendering requires both collection and material id, with no fallback to unrelated images', () => {
  const load = loader({ mocks: { '@/stores/playSessionStore': { usePlaySessionStore: () => ({}) },
    '@/services/auth': { currentToken: () => 'synthetic-account-a', sessionScope: async () => 'account-scope' },
    '@/lib/config': { API_BASE_URL: 'http://127.0.0.1:9999' },
  } });
  const { MaterialAssetContext, MaterialImages } = load('src/components/play/AuthorizedImage.tsx');
  const owner = { kind: 'play', id: 'play-one', scope: 'account-scope', visuals: [
    { id: 'allowed', collection: 'evidence', material_id: 'same-id', label: '已获物证原图' },
    { id: 'other-collection', collection: 'knowledge', material_id: 'same-id', label: '另一类资料图片' },
    { id: 'other-material', collection: 'evidence', material_id: 'different', label: '另一份物证图片' },
  ] };
  const render = props => renderToStaticMarkup(React.createElement(MaterialAssetContext.Provider, { value: owner }, React.createElement(MaterialImages, props)));
  const html = render({ collection: 'evidence', materialId: 'same-id' });
  assert.match(html, /已获物证原图/);
  assert.doesNotMatch(html, /另一类|另一份|blob:|Bearer/);
  assert.equal(render({ materialId: 'same-id' }), '');
  assert.equal(render({ collection: 'memory', materialId: 'same-id' }), '');
});

function assetHarness(options = {}) {
  let token = 'synthetic-account-a';
  let scope = 'scope-a';
  const calls = [];
  const response = { ok: true, status: 200, headers: new Headers({ 'Content-Type': 'image/png' }),
    blob: async () => new Blob(['synthetic-image'], { type: 'image/png' }) };
  const load = loader({ globals: { fetch: async (url, init) => { calls.push({ url, init }); return options.response?.() ?? response; } }, mocks: {
    '@/services/auth': { currentToken: () => token, sessionScope: async () => scope },
    '@/lib/config': { API_BASE_URL: 'http://127.0.0.1:9999/' },
  } });
  return { read: load('src/services/playAssets.ts').readPlayImage, calls,
    owner: { kind: 'play', id: 'play-a', scope: 'scope-a' },
    setToken: value => { token = value; }, setScope: value => { scope = value; } };
}

test('play and opening image fetches use bound authorized endpoints and a header, never token URLs or a proxy', async () => {
  const h = assetHarness();
  for (const kind of ['play', 'opening']) {
    const blob = await h.read({ ...h.owner, kind, id: 'id/escaped' }, 'visual/a');
    assert.equal(blob.type, 'image/png');
  }
  assert.equal(h.calls[0].url, 'http://127.0.0.1:9999/api/fusion/package-plays/id%2Fescaped/images/visual%2Fa');
  assert.equal(h.calls[1].url, 'http://127.0.0.1:9999/api/fusion/package-sessions/id%2Fescaped/images/visual%2Fa');
  for (const { url, init } of h.calls) {
    assert.equal(init.headers.Authorization, 'Bearer synthetic-account-a');
    assert.equal(init.cache, 'no-store');
    assert.equal(init.credentials, 'omit');
    assert.equal(init.redirect, 'error');
    assert.doesNotMatch(url, /synthetic-account|_next|token=/);
  }
});

test('missing identity, a different account scope, or an already aborted request cannot fetch images', async () => {
  const h = assetHarness();
  h.setToken(null);
  await assert.rejects(h.read(h.owner, 'a'), /登录身份/);
  h.setToken('synthetic-account-a'); h.setScope('scope-b');
  await assert.rejects(h.read(h.owner, 'a'), /登录身份/);
  h.setScope('scope-a');
  const controller = new AbortController(); controller.abort();
  await assert.rejects(h.read(h.owner, 'a', controller.signal), /取消/);
  assert.equal(h.calls.length, 0);
});

test('identity replacement during either response or blob decoding rejects the late image', async () => {
  const pendingResponse = deferred();
  const first = assetHarness({ response: () => pendingResponse.promise });
  const reading = first.read(first.owner, 'a');
  await Promise.resolve();
  first.setToken('synthetic-account-b');
  pendingResponse.resolve({ ok: true });
  await assert.rejects(reading, /登录身份/);

  const pendingBlob = deferred(); let decoding;
  const started = new Promise(resolve => { decoding = resolve; });
  const second = assetHarness({ response: () => ({ ok: true, headers: new Headers({ 'Content-Type': 'image/jpeg' }),
    blob: () => { decoding(); return pendingBlob.promise; } }) });
  const another = second.read(second.owner, 'a');
  await started;
  second.setToken('synthetic-account-b');
  pendingBlob.resolve(new Blob(['image']));
  await assert.rejects(another, /登录身份/);
});

test('HTTP denial and non-raster content are rejected without accepting a blob', async () => {
  for (const response of [
    { ok: false, status: 401 },
    { ok: false, status: 404 },
    { ok: true, headers: new Headers({ 'Content-Type': 'image/svg+xml' }) },
    { ok: true, headers: new Headers({ 'Content-Type': 'text/html' }) },
  ]) {
    let read = false;
    const h = assetHarness({ response: () => ({ ...response, blob() { read = true; throw new Error('unexpected'); } }) });
    await assert.rejects(h.read(h.owner, 'a'));
    assert.equal(read, false);
  }
});

function resourceHarness(overrides = {}) {
  let token = 'synthetic-account-a';
  const calls = [], snapshots = [], created = [], revoked = [];
  const listeners = new Map();
  const load = loader({ globals: {
    AbortController,
    URL: { createObjectURL(blob) { created.push(blob); return 'blob:private-' + created.length; }, revokeObjectURL(url) { revoked.push(url); } },
    window: { addEventListener(name, handler) { listeners.set(name, handler); }, removeEventListener(name) { listeners.delete(name); } },
  }, mocks: {
    '@/services/auth': { currentToken: () => token },
    '@/services/playAssets': { readPlayImage: async (...args) => { calls.push(args); return overrides.read?.(...args) ?? new Blob(['image']); } },
    '@/lib/playImageOrientation': { playImageRotation: async blob => overrides.rotation ? overrides.rotation(blob) : 270 },
  } });
  const resource = load('src/lib/playImageResource.ts').createPlayImageResource({ kind: 'play', id: 'p', scope: 'scope-a' }, 'v', value => snapshots.push(value));
  return { resource, calls, snapshots, created, revoked, listeners, setToken: value => { token = value; } };
}

test('image resource coalesces loads, uses verified rotation, and revokes its single local blob on disposal', async () => {
  const wait = deferred();
  const h = resourceHarness({ read: () => wait.promise });
  const first = h.resource.load();
  await h.resource.load();
  assert.equal(h.calls.length, 1);
  wait.resolve(new Blob(['image'])); await first;
  assert.equal(h.snapshots.at(-1).rotation, 270);
  assert.equal(h.snapshots.at(-1).url, 'blob:private-1');
  h.resource.rotate(); assert.equal(h.snapshots.at(-1).rotation, 0);
  await h.resource.load(); assert.equal(h.calls.length, 1);
  h.resource.dispose();
  assert.deepEqual(h.revoked, ['blob:private-1']);
  assert.equal(h.listeners.size, 0);
  assert.equal(h.calls[0][2].aborted, false);
});

test('a storage identity change clears displayed private images and permanently disables that resource', async () => {
  const h = resourceHarness(); await h.resource.load();
  h.setToken('synthetic-account-b'); h.listeners.get('storage')();
  assert.equal(h.snapshots.at(-1).url, '');
  assert.equal(h.snapshots.at(-1).invalid, true);
  assert.deepEqual(h.revoked, ['blob:private-1']);
  await h.resource.load(); assert.equal(h.calls.length, 1);
  h.setToken('synthetic-account-a'); await h.resource.load();
  assert.equal(h.calls.length, 1, 'an invalidated resource must never revive');
  h.resource.dispose();
});

test('unmount and identity replacement during request or orientation decoding never publish a late blob URL', async () => {
  const request = deferred(); const first = resourceHarness({ read: () => request.promise });
  const reading = first.resource.load(); first.resource.dispose();
  assert.equal(first.calls[0][2].aborted, true);
  request.resolve(new Blob(['image'])); await reading;
  assert.equal(first.created.length, 0);
  const hash = deferred(); let started;
  const hashing = new Promise(resolve => { started = resolve; });
  const second = resourceHarness({ rotation: () => { started(); return hash.promise; } });
  const another = second.resource.load(); await hashing;
  second.setToken('synthetic-account-b'); second.listeners.get('focus')();
  hash.resolve(180); await another;
  assert.equal(second.created.length, 0);
  assert.equal(second.snapshots.at(-1).invalid, true);
  second.resource.dispose();
});

test('an unrecognized image fingerprint remains upright instead of inheriting another card ID orientation', async () => {
  const { playImageRotation } = loader({ globals: { crypto: webcrypto, Uint8Array } })('src/lib/playImageOrientation.ts');
  assert.equal(await playImageRotation(new Blob(['a new synthetic card'])), 0);
});

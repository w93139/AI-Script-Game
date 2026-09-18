const test = require('node:test');
const assert = require('node:assert/strict');
const { loader, storage } = require('./ts-loader.cjs');

test('saving or clearing an account cancels same-page speech immediately and old bindings never revive', () => {
  const window = new EventTarget(), localStorage = storage();
  const load = loader({ globals: { window, localStorage, Event }, mocks: { '@/lib/http': { http: {} } } });
  const auth = load('src/services/auth.ts');
  auth.saveToken({ access_token: 'fixture-a' });
  const { watchPackagePlayAuth } = load('src/services/playSpeechAuth.ts');
  let changes = 0;
  const watch = watchPackagePlayAuth(() => changes++);
  assert.equal(watch.isCurrent(), true);
  auth.saveToken({ access_token: 'fixture-b' });
  assert.equal(changes, 1); assert.equal(watch.isCurrent(), false);
  auth.saveToken({ access_token: 'fixture-a' });
  assert.equal(changes, 2); assert.equal(watch.isCurrent(), false);
  const current = watchPackagePlayAuth(() => changes++);
  auth.clearToken();
  assert.equal(current.isCurrent(), false); assert.equal(changes, 4);
  watch.dispose(); current.dispose();
  auth.saveToken({ access_token: 'fixture-c' });
  assert.equal(changes, 4);
});

test('cross-tab and focus events invalidate speech when storage changes outside auth helpers', () => {
  const window = new EventTarget(); let token = 'fixture-a', changes = 0;
  const { watchPackagePlayAuth } = loader({ globals: { window }, mocks: { '@/services/auth': { currentToken: () => token } } })('src/services/playSpeechAuth.ts');
  const guard = watchPackagePlayAuth(() => changes++);
  token = 'fixture-b'; window.dispatchEvent(new Event('storage'));
  assert.equal(guard.isCurrent(), false); assert.equal(changes, 1);
  token = 'fixture-c'; window.dispatchEvent(new Event('focus'));
  assert.equal(changes, 2); guard.dispose();
});

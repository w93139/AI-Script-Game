const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { loader, storage } = require('./ts-loader.cjs');
const { renderToStaticMarkup } = require('react-dom/server');
const elements = (tree, type) => Array.isArray(tree) ? tree.flatMap(x => elements(x, type)) : !React.isValidElement(tree) ? []
  : [...(tree.type === type ? [tree] : []), ...elements(tree.props.children, type)];

function harness({ call = false, locked = false } = {}) {
  const sessionStorage = storage(), sends = [];
  const noteKey = 'draft:owner-scope:play-a:phase-a';
  sessionStorage.setItem(`${noteKey}:public`, '原公开草稿');
  sessionStorage.setItem(`${noteKey}:private:call-a`, '原私聊草稿');
  const play = { play_id: 'play-a', revision: 9, current_phase: { id: 'phase-a' }, selected_character_id: 'a',
    characters: [{ id: 'a', name: '甲' }, { id: 'b', name: '乙' }], discussion: { entries: [] },
    single_player: { topics: [], turns: [] }, full_game: { call: call ? { id: 'call-a', character_ids: ['a','b'] } : null, phone_busy: call, private_discussion: [] } };
  const slots = []; let slot = 0;
  const Voice = () => null;
  const { Exchange } = loader({ globals: { sessionStorage }, mocks: {
    react: { ...React, useState(initial) { const i = slot++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], value => { slots[i] = value; }]; } },
    '@/stores/playSessionStore': { usePlaySessionStore: select => select({ send: async (...args) => { sends.push(args); return true; }, busy: false }) },
    './AuthorizedImage': { MaterialImages: () => null }, './PlayVoiceInput': Voice,
  } })('src/components/play/GamePanels.tsx');
  return { sends, sessionStorage, noteKey, Voice, render() { slot = 0; return Exchange({ play, locked, noteKey, ownerScope: 'owner-scope' }); } };
}

test('public voice appends to the saved statement draft and only the explicit record button sends it', async () => {
  const h = harness();
  const [voice] = elements(h.render(), h.Voice);
  assert.equal(voice.props.ownerId, 'owner-scope'); assert.equal(voice.props.playId, 'play-a');
  assert.equal(voice.props.phaseId, 'phase-a'); assert.equal(voice.props.revision, 9);
  assert.equal(voice.props.channel, 'PUBLIC'); assert.equal(voice.props.disabled, false);
  voice.props.onChange('原公开草稿\n校对后的话');
  assert.equal(h.sessionStorage.getItem(`${h.noteKey}:public`), '原公开草稿\n校对后的话');
  assert.deepEqual(h.sends, []);
  const send = elements(h.render(), 'button').find(button => button.props.children === '记录公开发言');
  await send.props.onClick(); await Promise.resolve();
  assert.equal(h.sends.length, 1); assert.equal(h.sends[0][0], 'discussion');
  assert.equal(h.sends[0][1].text, '原公开草稿\n校对后的话');
});

test('private voice binds the current call and never overwrites the public draft', () => {
  const h = harness({ call: true });
  const [publicVoice, privateVoice] = elements(h.render(), h.Voice);
  assert.equal(publicVoice.props.disabled, true);
  assert.equal(privateVoice.props.channel, 'PRIVATE'); assert.equal(privateVoice.props.callId, 'call-a');
  assert.equal(privateVoice.props.value, '原私聊草稿'); assert.equal(privateVoice.props.disabled, false);
  privateVoice.props.onChange('原私聊草稿\n私聊校对内容');
  assert.equal(h.sessionStorage.getItem(`${h.noteKey}:private:call-a`), '原私聊草稿\n私聊校对内容');
  assert.equal(h.sessionStorage.getItem(`${h.noteKey}:public`), '原公开草稿');
  assert.deepEqual(h.sends, []);
});

test('pending game operations disable both recorders while the finite question flow stays separate', () => {
  const h = harness({ call: true, locked: true });
  assert.equal(elements(h.render(), h.Voice).every(voice => voice.props.disabled), true);
  const html = renderToStaticMarkup(h.render());
  assert.match(html, /不会自动请求 AI 回答/);
  assert.match(html, /需要回应时，请在上方选择可问的问题/);
});

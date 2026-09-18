import { create } from 'zustand';
import axios from 'axios';
import { ensureSession, currentToken, sessionScope } from '@/services/auth';
import { command, createPlay, createSession, findPlay, getPlay, getSession, listReleases,
  type CommandBody, type CommandEndpoint } from '@/services/play';
import { newKey } from '@/lib/id';
import { errorCode } from '@/lib/http';
import type { OpeningSession, PlayView, Release } from '@/types/api';
import type { TopicAction } from '@/types/packagePlay';

type TopicSelection = Extract<TopicAction, { action: 'ASK_TOPIC' }>['payload'];

export type SessionMode = 'connecting' | 'selecting' | 'opening' | 'live' | 'error';
type Attempt = { endpoint: CommandEndpoint; body: CommandBody };
interface PlaySessionState {
  mode: SessionMode; releases: Release[]; opening: OpeningSession | null; play: PlayView | null;
  error: string | null; busy: boolean; unresolved: Attempt | null; scope: string;
  bootstrap: (resume?: { playId?: string; openingSessionId?: string }) => Promise<void>;
  preview: (releaseId: number, characterId: string) => Promise<void>;
  begin: () => Promise<void>;
  refresh: () => Promise<void>;
  send: (endpoint: CommandEndpoint, payload: Record<string, unknown>, frozen?: CommandBody) => Promise<boolean>;
  askTopic: (selection: TopicSelection) => Promise<boolean>;
  checkRequest: () => Promise<boolean>;
  invalidate: () => void;
}
let generation = 0;
function attemptSlot(scope: string, playId: string) { return `play-attempt:${scope}:${playId}`; }
function readAttempt(scope: string, playId: string): Attempt | null {
  const value = sessionStorage.getItem(attemptSlot(scope, playId));
  if (!value) return null;
  const parsed = JSON.parse(value) as Attempt;
  const allowed = ['actions', 'discussion', 'table', 'decisions', 'guided', 'responses', 'private-responses', 'topic', 'phone-pause', 'finale-motivations'];
  if (!allowed.includes(parsed.endpoint) || !parsed.body?.idempotency_key || !Number.isInteger(parsed.body.expected_revision)) {
    throw new Error('本地请求记录无法读取，请保留记录并联系维护者。');
  }
  return parsed;
}
function stableKey(scope: string, label: string) {
  const slot = `play-create:${scope}:${label}`;
  const old = sessionStorage.getItem(slot);
  if (old) return old;
  const key = newKey();
  sessionStorage.setItem(slot, key);
  return key;
}
function rejected(err: unknown) {
  return axios.isAxiosError(err) && !!err.response && err.response.status >= 400 && err.response.status < 500;
}

export const usePlaySessionStore = create<PlaySessionState>((set, get) => {
  let identityToken: string | null = null;
  const identityValid = () => {
    if (identityToken && identityToken === currentToken()) return true;
    get().invalidate();
    return false;
  };
  const isCurrent = (epoch: number, token: string | null) => {
    if (epoch !== generation) return false;
    if (token !== currentToken()) { get().invalidate(); return false; }
    return true;
  };
  async function dispatch(attempt: Attempt, checking = false): Promise<boolean> {
    const state = get();
    const play = state.play;
    if (!play || state.busy || (state.unresolved && !checking)) return false;
    if (!identityValid()) return false;
    const epoch = generation;
    const token = currentToken();
    set({ busy: true, error: null });
    try {
      // Persist before dispatch; if storage fails, no request is sent.
      sessionStorage.setItem(attemptSlot(state.scope, play.play_id), JSON.stringify(attempt));
      set({ unresolved: attempt });
      const fresh = await command(play.play_id, attempt.endpoint, attempt.body);
      if (!isCurrent(epoch, token)) return false;
      if (!fresh.pending_ai) sessionStorage.removeItem(attemptSlot(state.scope, play.play_id));
      const topicResult = fresh.single_player?.turns.find(t =>
        t.phase_id === fresh.current_phase.id && t.reply_request?.idempotency_key === attempt.body.idempotency_key);
      // Topic failures have a durable, local recovery card. last_ai_status is
      // historical: a later successful investigation/fallback must not repeat it.
      const modelCommand = ['responses', 'private-responses', 'decisions', 'finale-motivations'].includes(attempt.endpoint);
      set({ play: fresh, unresolved: fresh.pending_ai ? attempt : null,
        error: !fresh.pending_ai && modelCommand && !topicResult && fresh.last_ai_status && fresh.last_ai_status !== 'OK'
          ? '本次角色回应未成功。结果已保存，可以继续调查。' : null });
      return !fresh.pending_ai;
    } catch (err) {
      if (!isCurrent(epoch, token)) return false;
      if (rejected(err)) {
        sessionStorage.removeItem(attemptSlot(state.scope, play.play_id));
        set({ unresolved: null });
        try {
          const fresh = await getPlay(play.play_id);
          if (isCurrent(epoch, token)) set({ play: fresh });
        } catch { /* Preserve the last authorized view and explicit error. */ }
      }
      if (!isCurrent(epoch, token)) return false;
      set({ error: errorCode(err) });
      return false;
    } finally {
      if (epoch === generation) set({ busy: false });
    }
  }
  return {
    mode: 'connecting', releases: [], opening: null, play: null, error: null,
    busy: false, unresolved: null, scope: '',
    invalidate: () => {
      generation += 1;
      set({ play: null, opening: null, releases: [], unresolved: null, busy: false, mode: 'error', error: '登录身份已变化，请重新打开游戏。' });
    },
    bootstrap: async (resume) => {
      const epoch = ++generation;
      let token = currentToken();
      set({ mode: 'connecting', play: null, opening: null, error: null, unresolved: null, busy: false });
      try {
        await ensureSession();
        token = currentToken();
        const scope = await sessionScope();
        const valid = () => isCurrent(epoch, token);
        if (!valid()) return;
        identityToken = token;
        if (resume?.playId) {
          const play = await getPlay(resume.playId);
          const unresolved = readAttempt(scope, play.play_id);
          if (valid()) set({ mode: 'live', play, scope, unresolved });
        } else if (resume?.openingSessionId) {
          const opening = await getSession(resume.openingSessionId);
          if (valid()) set({ mode: 'opening', opening, scope });
        } else {
          const releases = await listReleases();
          if (valid()) set({ mode: 'selecting', releases, scope });
        }
      } catch (err) {
        if (isCurrent(epoch, token)) set({ mode: 'error', error: errorCode(err) });
      }
    },
    preview: async (releaseId, characterId) => {
      if (get().busy) return;
      if (!identityValid()) return;
      const state = get(); const epoch = generation; const token = currentToken();
      set({ busy: true, error: null });
      try {
        const opening = await createSession({ release_id: releaseId, character_id: characterId,
          idempotency_key: stableKey(state.scope, `${releaseId}:${characterId}`) });
        if (isCurrent(epoch, token)) set({ mode: 'opening', opening });
      } catch (err) { if (isCurrent(epoch, token)) set({ error: errorCode(err) }); }
      finally { if (epoch === generation) set({ busy: false }); }
    },
    begin: async () => {
      const { opening, scope, busy } = get();
      if (!opening || busy) return;
      if (!identityValid()) return;
      const epoch = generation; const token = currentToken(); set({ busy: true, error: null });
      try {
        const existing = await findPlay(opening.session_id);
        if (!isCurrent(epoch, token)) return;
        const play = existing ?? await createPlay({ opening_session_id: opening.session_id,
          idempotency_key: stableKey(scope, opening.session_id) });
        if (isCurrent(epoch, token)) {
          set({ mode: 'live', play, unresolved: readAttempt(scope, play.play_id) });
          sessionStorage.removeItem(`play-create:${scope}:${opening.release_id}:${opening.selected_character_id}`);
        }
      } catch (err) { if (isCurrent(epoch, token)) set({ error: errorCode(err) }); }
      finally { if (epoch === generation) set({ busy: false }); }
    },
    refresh: async () => {
      const { play, busy } = get(); if (!play || busy) return;
      if (!identityValid()) return;
      const epoch = generation; const token = currentToken(); set({ busy: true, error: null });
      try {
        const fresh = await getPlay(play.play_id);
        if (isCurrent(epoch, token)) set({ play: fresh });
      } catch (err) { if (isCurrent(epoch, token)) set({ error: errorCode(err) }); }
      finally { if (epoch === generation) set({ busy: false }); }
    },
    send: (endpoint, payload, frozen) => {
      const play = get().play;
      if (!play) return Promise.resolve(false);
      return dispatch({ endpoint, body: frozen ?? { ...payload, expected_revision: play.revision, idempotency_key: newKey() } });
    },
    askTopic: async selection => {
      const original = get();
      const play = original.play;
      if (!play || original.busy || original.unresolved || play.pending_ai || !play.single_player?.available) return false;
      const epoch = generation;
      const token = currentToken();
      const key = newKey();
      const saved = await dispatch({ endpoint: 'topic', body: {
        schema_version: 'package-topic-command/1.0', action: 'ASK_TOPIC', payload: selection,
        expected_revision: play.revision, idempotency_key: key,
      } });
      if (!saved || !isCurrent(epoch, token)) return false;
      const state = get();
      const fresh = state.play;
      if (!fresh || fresh.play_id !== play.play_id || state.scope !== original.scope ||
          fresh.current_phase.id !== play.current_phase.id || state.busy || state.unresolved || fresh.pending_ai) return false;
      const receipt = fresh.single_player?.last_command;
      if (receipt?.action !== 'ASK_TOPIC' || receipt.idempotency_key !== key) return false;
      const turn = fresh.single_player?.turns.find(t => t.id === `topic-${receipt.sequence}` &&
        t.phase_id === fresh.current_phase.id && t.topic_id === selection.topic_id &&
        t.character_id === selection.character_id && t.intent_id === selection.intent_id && t.channel === selection.channel);
      // Only this explicit click may start the newly saved question. Reloads,
      // unknown results and unavailable AI keep the server's recovery choices.
      if (!turn || turn.status !== 'READY' || turn.can_fallback || !turn.reply_request ||
          turn.reply_request.expected_revision !== fresh.revision) return true;
      if (selection.channel === 'PRIVATE' && (!play.full_game?.call ||
          fresh.full_game?.call?.id !== play.full_game.call.id ||
          !fresh.full_game.call.character_ids.includes(selection.character_id))) return false;
      if (selection.channel === 'PUBLIC' && fresh.full_game?.phone_busy) return false;
      return dispatch({ endpoint: selection.channel === 'PRIVATE' ? 'private-responses' : 'responses', body: turn.reply_request });
    },
    checkRequest: () => {
      const attempt = get().unresolved;
      return attempt ? dispatch(attempt, true) : Promise.resolve(false);
    },
  };
});

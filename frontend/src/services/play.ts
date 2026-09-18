import { http } from "@/lib/http";
import { currentToken } from './auth';
import type {
  ActionBody,
  AskBody,
  CreatePlayBody,
  CreateSessionBody,
  LibraryResult,
  OpeningSession,
  PlayView,
  Release,
  SpeakBody,
} from "@/types/api";

interface Envelope<T> {
  success: boolean;
  data: T;
}

async function unwrap<T>(
  promise: Promise<{ data: Envelope<T> }>,
): Promise<T> {
  const res = await promise;
  if (res.data?.success !== true || !Object.hasOwn(res.data, 'data')) {
    throw new Error('未收到完整游戏结果，请核对原请求。');
  }
  return res.data.data;
}

export function listReleases() {
  return unwrap<Release[]>(http.get("/api/fusion/package-releases"));
}

export function createSession(body: CreateSessionBody) {
  return unwrap<OpeningSession>(
    http.post("/api/fusion/package-sessions", body),
  );
}

export function getSession(sessionId: string) {
  return unwrap<OpeningSession>(
    http.get(`/api/fusion/package-sessions/${sessionId}`),
  );
}

export function findPlay(openingSessionId: string) {
  return unwrap<PlayView | null>(
    http.get("/api/fusion/package-plays", {
      params: { opening_session_id: openingSessionId },
    }),
  );
}

export function createPlay(body: CreatePlayBody) {
  return unwrap<PlayView>(http.post("/api/fusion/package-plays", body));
}

export function getPlay(playId: string) {
  return unwrap<PlayView>(http.get(`/api/fusion/package-plays/${playId}`));
}

export function act(playId: string, body: ActionBody) {
  return unwrap<PlayView>(
    http.post(`/api/fusion/package-plays/${playId}/actions`, body),
  );
}

export function ask(playId: string, body: AskBody) {
  return unwrap<PlayView>(
    http.post(`/api/fusion/package-plays/${playId}/ask`, body),
  );
}

export function speak(playId: string, body: SpeakBody) {
  return unwrap<PlayView>(
    http.post(`/api/fusion/package-plays/${playId}/discussion`, body),
  );
}

export function listLibrary(offset = 0, limit = 20) {
  return unwrap<LibraryResult>(
    http.get("/api/fusion/package-play-library", {
      params: { offset: String(offset), limit: String(limit) },
    }),
  );
}

export type CommandEndpoint = 'actions' | 'discussion' | 'table' | 'decisions' | 'guided'
  | 'responses' | 'private-responses' | 'topic' | 'phone-pause' | 'finale-motivations';
export type CommandBody = { expected_revision: number; idempotency_key: string; [key: string]: unknown };

export async function command(playId: string, endpoint: CommandEndpoint, body: CommandBody) {
  const token = currentToken();
  const result = await unwrap<PlayView>(http.post(`/api/fusion/package-plays/${encodeURIComponent(playId)}/${endpoint}`, body));
  if (currentToken() !== token) throw new Error('登录身份已变化，请重新打开原局。');
  return result;
}

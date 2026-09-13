import { create } from "zustand";
import { anonymousLogin, saveToken } from "@/services/auth";
import {
  act,
  ask,
  createPlay,
  createSession,
  findPlay,
  getPlay,
  getSession,
  listReleases,
  speak,
} from "@/services/play";
import { newKey } from "@/lib/id";
import { errorCode } from "@/lib/http";
import type { ActionBody, PlayActionName, PlayView, ReleaseCharacter } from "@/types/api";

export type SessionMode = "connecting" | "live" | "mock";

interface PlaySessionState {
  mode: SessionMode;
  title: string;
  play: PlayView | null;
  characters: ReleaseCharacter[];
  error: string | null;
  /** 建立登录 → 选剧本/角色 → 开场 → 试玩 的链路；可传入 play_id 或 opening_session_id 续玩；任一步失败回退 mock。 */
  bootstrap: (resume?: { playId?: string; openingSessionId?: string }) => Promise<void>;
  refresh: () => Promise<void>;
  performAction: (action: PlayActionName, target?: ActionBody["target"]) => Promise<void>;
  speakText: (text: string) => Promise<void>;
  askQuestion: (characterId: string, question: string) => Promise<void>;
}

export const usePlaySessionStore = create<PlaySessionState>((set, get) => ({
  mode: "connecting",
  title: "孽岛疑云",
  play: null,
  characters: [],
  error: null,

  bootstrap: async (resume) => {
    set({ mode: "connecting", error: null });
    try {
      const token = await anonymousLogin();
      saveToken(token);

      if (resume?.playId) {
        const play = await getPlay(resume.playId);
        set({
          mode: "live",
          play,
          title: play.script?.title ?? "剧本",
          characters: play.characters ?? [],
          error: null,
        });
        return;
      }

      const releases = await listReleases();
      if (!releases.length) throw new Error("NO_RELEASES");
      const release = releases[0];
      const character = release.characters[0];
      if (!character) throw new Error("NO_CHARACTERS");

      const opening = resume?.openingSessionId
        ? await getSession(resume.openingSessionId)
        : await createSession({
            release_id: release.id,
            character_id: character.id,
            idempotency_key: newKey(),
          });

      const existing = await findPlay(opening.session_id);
      const play =
        existing ??
        (await createPlay({
          opening_session_id: opening.session_id,
          idempotency_key: newKey(),
        }));

      set({
        mode: "live",
        play,
        title: opening.script?.title ?? release.title,
        characters: opening.characters,
        error: null,
      });
    } catch (err) {
      set({ mode: "mock", play: null, error: errorCode(err) });
    }
  },

  refresh: async () => {
    const { play } = get();
    if (!play) return;
    try {
      set({ play: await getPlay(play.play_id), error: null });
    } catch (err) {
      set({ error: errorCode(err) });
    }
  },

  performAction: async (action, target = null) => {
    const { play } = get();
    if (!play) return;
    try {
      const fresh = await act(play.play_id, {
        expected_revision: play.revision ?? 0,
        idempotency_key: newKey(),
        action,
        target,
      });
      set({ play: fresh, error: null });
    } catch (err) {
      set({ error: errorCode(err) });
    }
  },

  speakText: async (text) => {
    const { play } = get();
    if (!play) return;
    try {
      const fresh = await speak(play.play_id, {
        schema_version: "package-discussion-command/1.0",
        action: "SPEAK",
        expected_revision: play.revision ?? 0,
        idempotency_key: newKey(),
        text,
      });
      set({ play: fresh, error: null });
    } catch (err) {
      set({ error: errorCode(err) });
    }
  },

  askQuestion: async (characterId, question) => {
    const { play } = get();
    if (!play) return;
    try {
      const fresh = await ask(play.play_id, {
        expected_revision: play.revision ?? 0,
        idempotency_key: newKey(),
        character_id: characterId,
        question,
      });
      set({ play: fresh, error: null });
    } catch (err) {
      set({ error: errorCode(err) });
    }
  },
}));

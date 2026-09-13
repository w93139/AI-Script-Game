import { create } from "zustand";
import { anonymousLogin, saveToken } from "@/services/auth";
import {
  act,
  createPlay,
  createSession,
  findPlay,
  getPlay,
  listReleases,
} from "@/services/play";
import { newKey } from "@/lib/id";
import { errorCode } from "@/lib/http";
import type { PlayActionName, PlayView } from "@/types/api";

export type SessionMode = "connecting" | "live" | "mock";

interface PlaySessionState {
  mode: SessionMode;
  title: string;
  play: PlayView | null;
  error: string | null;
  /** 建立匿名登录 → 选剧本/角色 → 开场 → 试玩 的完整链路；任一步失败回退 mock。 */
  bootstrap: () => Promise<void>;
  refresh: () => Promise<void>;
  performAction: (action: PlayActionName) => Promise<void>;
}

export const usePlaySessionStore = create<PlaySessionState>((set, get) => ({
  mode: "connecting",
  title: "孽岛疑云",
  play: null,
  error: null,

  bootstrap: async () => {
    set({ mode: "connecting", error: null });
    try {
      const token = await anonymousLogin();
      saveToken(token);

      const releases = await listReleases();
      if (!releases.length) throw new Error("NO_RELEASES");
      const release = releases[0];
      const character = release.characters[0];
      if (!character) throw new Error("NO_CHARACTERS");

      const opening = await createSession({
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

      set({ mode: "live", play, title: release.title, error: null });
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

  performAction: async (action: PlayActionName) => {
    const { play } = get();
    if (!play) return;
    try {
      const fresh = await act(play.play_id, {
        expected_revision: play.revision ?? 0,
        idempotency_key: newKey(),
        action,
      });
      set({ play: fresh, error: null });
    } catch (err) {
      set({ error: errorCode(err) });
    }
  },
}));

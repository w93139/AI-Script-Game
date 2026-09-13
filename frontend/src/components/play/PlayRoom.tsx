"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { usePlaySessionStore } from "@/stores/playSessionStore";
import { usePlayUiStore } from "@/stores/playStore";
import { PhaseBar } from "./PhaseBar";
import { NarrativeStream } from "./NarrativeStream";
import { ArchiveDrawer } from "./ArchiveDrawer";
import { ActionBar } from "./ActionBar";
import { Composer } from "./Composer";
import { MOCK_DEPOSITIONS, MOCK_TITLE } from "@/lib/mock";
import type { PlayView } from "@/types/api";
import type { ActId, DepositionEntry } from "@/types/play";

function actFor(play: PlayView | null): ActId {
  if (!play) return "investigation";
  if (play.settled) return "finale";
  if (play.mechanics) return "investigation";
  return "reading";
}

function depositionsFor(play: PlayView | null): DepositionEntry[] {
  if (!play) return [];
  const out: DepositionEntry[] = [];
  let seq = 0;
  for (const d of play.dialogue ?? []) {
    out.push({
      id: `dlg-${seq}`,
      seq: ++seq,
      speaker: d.speaker,
      self: d.self,
      text: d.text,
    });
  }
  for (const e of play.discussion?.entries ?? []) {
    out.push({ id: e.id, seq: ++seq, speaker: e.speaker, text: e.text });
  }
  return out;
}

export function PlayRoom() {
  const {
    mode,
    title,
    play,
    error,
    bootstrap,
    speakText,
    askQuestion,
    characters,
  } = usePlaySessionStore();
  const archiveOpen = usePlayUiStore((s) => s.archiveOpen);
  const actionMode = usePlayUiStore((s) => s.actionMode);
  const setCurrentAct = usePlayUiStore((s) => s.setCurrentAct);

  const [mockEntries, setMockEntries] = useState<DepositionEntry[]>([]);

  const searchParams = useSearchParams();
  const playId = searchParams.get("play_id");
  const openingSessionId = searchParams.get("opening_session_id");

  useEffect(() => {
    void bootstrap({
      playId: playId ?? undefined,
      openingSessionId: openingSessionId ?? undefined,
    });
  }, [bootstrap, playId, openingSessionId]);

  useEffect(() => {
    setCurrentAct(actFor(play));
  }, [play, setCurrentAct]);

  const isLive = mode === "live" && play;
  const liveDepositions = isLive ? depositionsFor(play) : [];
  const entries = isLive
    ? liveDepositions.length
      ? liveDepositions
      : MOCK_DEPOSITIONS
    : [...MOCK_DEPOSITIONS, ...mockEntries];

  const points = play?.mechanics?.remaining_points;
  const settlement = play?.settlement;

  const send = (text: string) => {
    if (isLive) {
      if (actionMode === "ask") {
        const target =
          characters.find((c) => c.id !== play.selected_character?.id) ??
          characters[0];
        if (target) {
          void askQuestion(target.id, text);
          return;
        }
      }
      void speakText(text);
      return;
    }
    setMockEntries((prev) => [
      ...prev,
      {
        id: `mock-${prev.length}`,
        seq: MOCK_DEPOSITIONS.length + prev.length + 1,
        speaker: "你",
        self: true,
        text,
      },
    ]);
  };

  const placeholder =
    actionMode === "ask"
      ? "向角色提问…（回车发送，Esc 取消）"
      : "公开发言…（回车发送，Esc 取消）";

  return (
    <div className="flex h-screen flex-col">
      <PhaseBar title={isLive ? title : MOCK_TITLE} points={points} />

      <div className="relative flex min-h-0 flex-1">
        <main className="flex-1 overflow-y-auto px-8 py-8">
          <div className="mx-auto max-w-2xl">
            {mode === "mock" && (
              <div className="mb-6 rounded-md border border-graphite/60 bg-carbon px-3 py-2 font-mono text-[11px] text-fog">
                离线演示模式 · 后端未连接（{error ?? "—"}）
              </div>
            )}
            {isLive && (
              <div className="mb-6 rounded-md border border-graphite/60 bg-carbon px-3 py-2 font-mono text-[11px] text-fog">
                已连接 · 本局 {play.play_id.slice(0, 12)}
              </div>
            )}

            {settlement && (
              <div className="mb-8 rounded-lg border border-acid-lime/30 bg-carbon p-5">
                <div className="font-mono text-[11px] tracking-widest text-acid-lime">
                  真相揭晓
                </div>
                <p className="mt-3 text-[15px] leading-relaxed text-mist">
                  {settlement.text}
                </p>
                {settlement.truths && settlement.truths.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {settlement.truths.map((t) => (
                      <li key={t.id} className="text-[13px] text-ash">
                        · {t.text}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <NarrativeStream entries={entries} />
          </div>
        </main>
        {archiveOpen && <ArchiveDrawer />}
      </div>

      {actionMode !== "idle" ? (
        <Composer placeholder={placeholder} onSend={send} />
      ) : (
        <ActionBar contact="唐小姐" />
      )}
    </div>
  );
}

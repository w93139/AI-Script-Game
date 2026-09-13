"use client";

import { useEffect } from "react";
import { usePlaySessionStore } from "@/stores/playSessionStore";
import { usePlayUiStore } from "@/stores/playStore";
import { PhaseBar } from "./PhaseBar";
import { NarrativeStream } from "./NarrativeStream";
import { ArchiveDrawer } from "./ArchiveDrawer";
import { ActionBar } from "./ActionBar";
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
  if (!play) return MOCK_DEPOSITIONS;
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
  return out.length ? out : MOCK_DEPOSITIONS;
}

export function PlayRoom() {
  const { mode, title, play, error, bootstrap } = usePlaySessionStore();
  const archiveOpen = usePlayUiStore((s) => s.archiveOpen);
  const setCurrentAct = usePlayUiStore((s) => s.setCurrentAct);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    setCurrentAct(actFor(play));
  }, [play, setCurrentAct]);

  const isLive = mode === "live" && play;
  const points = play?.mechanics?.remaining_points;

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
            <NarrativeStream entries={depositionsFor(play)} />
          </div>
        </main>
        {archiveOpen && <ArchiveDrawer />}
      </div>

      <ActionBar contact="唐小姐" />
    </div>
  );
}

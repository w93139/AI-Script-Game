"use client";

import { usePlayUiStore } from "@/stores/playStore";
import { PhaseBar } from "@/components/play/PhaseBar";
import { NarrativeStream } from "@/components/play/NarrativeStream";
import { ArchiveDrawer } from "@/components/play/ArchiveDrawer";
import { ActionBar } from "@/components/play/ActionBar";
import { MOCK_DEPOSITIONS, MOCK_TITLE } from "@/lib/mock";

export default function PlayPage() {
  const archiveOpen = usePlayUiStore((s) => s.archiveOpen);

  return (
    <div className="flex h-screen flex-col">
      <PhaseBar title={MOCK_TITLE} points={2} />

      <div className="flex min-h-0 flex-1">
        <main className="flex-1 overflow-y-auto px-8 py-8">
          <NarrativeStream entries={MOCK_DEPOSITIONS} />
        </main>
        {archiveOpen && <ArchiveDrawer />}
      </div>

      <ActionBar contact="唐小姐" />
    </div>
  );
}

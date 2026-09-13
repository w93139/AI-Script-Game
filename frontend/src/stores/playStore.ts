import { create } from "zustand";
import type { ActId } from "@/types/play";

export type ArchiveTab = "characters" | "evidence" | "memories" | "notes";

interface PlayUiState {
  archiveOpen: boolean;
  activeArchiveTab: ArchiveTab;
  currentAct: ActId;
  toggleArchive: () => void;
  setArchiveTab: (tab: ArchiveTab) => void;
  setCurrentAct: (act: ActId) => void;
}

export const usePlayUiStore = create<PlayUiState>((set) => ({
  archiveOpen: true,
  activeArchiveTab: "characters",
  currentAct: "investigation",
  toggleArchive: () => set((s) => ({ archiveOpen: !s.archiveOpen })),
  setArchiveTab: (tab) => set({ activeArchiveTab: tab }),
  setCurrentAct: (act) => set({ currentAct: act }),
}));

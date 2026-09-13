"use client";

import { HelpCircle, MessagesSquare, Phone, Search } from "lucide-react";
import { usePlayUiStore } from "@/stores/playStore";

interface Action {
  id: string;
  label: string;
  icon: React.ReactNode;
  primary?: boolean;
}

function actionsForAct(act: string, contact: string): Action[] {
  switch (act) {
    case "reading":
      return [
        { id: "next", label: "继续阅读", icon: <MessagesSquare size={15} />, primary: true },
      ];
    case "investigation":
      return [
        { id: "search", label: "调查书房", icon: <Search size={15} />, primary: true },
        { id: "discuss", label: "公开讨论", icon: <MessagesSquare size={15} /> },
        { id: "private", label: `私聊${contact}`, icon: <Phone size={15} /> },
        { id: "ask", label: "提问", icon: <HelpCircle size={15} /> },
      ];
    case "finale":
      return [
        { id: "vote", label: "投票", icon: <MessagesSquare size={15} />, primary: true },
      ];
    default:
      return [];
  }
}

export function ActionBar({ contact = "唐小姐" }: { contact?: string }) {
  const currentAct = usePlayUiStore((s) => s.currentAct);
  const actions = actionsForAct(currentAct, contact);

  return (
    <footer className="shrink-0 border-t border-graphite/60 px-5 py-3">
      <div className="mx-auto flex max-w-2xl items-center gap-2">
        {actions.map((action) => (
          <button
            key={action.id}
            className={
              action.primary
                ? "inline-flex items-center gap-1.5 rounded-md bg-acid-lime px-4 py-2 text-[14px] font-medium text-void transition-opacity hover:opacity-90"
                : "inline-flex items-center gap-1.5 rounded-md border border-graphite px-4 py-2 text-[13px] text-mist transition-colors hover:border-smoke"
            }
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>
    </footer>
  );
}

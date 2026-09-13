import type { DepositionEntry } from "@/types/play";
import { cn } from "@/lib/utils";

export function Deposition({ entry }: { entry: DepositionEntry }) {
  const { seq, speaker, self, text } = entry;
  return (
    <div className="flex gap-4">
      <span className="w-9 shrink-0 pt-0.5 text-right font-mono text-[12px] leading-6 text-fog">
        #{String(seq).padStart(2, "0")}
      </span>
      <div className={cn("min-w-0", self && "border-l-2 border-acid-lime pl-4")}>
        <div
          className={cn(
            "text-[13px] font-medium",
            self ? "text-acid-lime" : "text-mist",
          )}
        >
          {speaker}
        </div>
        <p className="mt-1 text-[15px] leading-relaxed text-mist">{text}</p>
      </div>
    </div>
  );
}

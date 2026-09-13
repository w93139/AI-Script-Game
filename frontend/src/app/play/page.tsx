import {
  HelpCircle,
  MessagesSquare,
  Phone,
  Search,
} from "lucide-react";

function Deposition({
  n,
  name,
  text,
  self = false,
}: {
  n: string;
  name: string;
  text: string;
  self?: boolean;
}) {
  return (
    <div className="flex gap-4">
      <span className="font-mono text-[12px] leading-6 text-fog">{n}</span>
      <div>
        <div
          className={
            self ? "text-[13px] font-medium text-acid-lime" : "text-[13px] font-medium text-mist"
          }
        >
          {name}
        </div>
        <p className="mt-1 text-[15px] leading-relaxed text-mist">{text}</p>
      </div>
    </div>
  );
}

export default function PlayPage() {
  return (
    <div className="flex h-screen flex-col">
      {/* 顶部 · 阶段刻度 */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-graphite/60 px-5">
        <div className="flex items-center gap-5">
          <span className="text-[14px] font-medium text-paper">孽岛疑云</span>
          <nav className="flex items-center gap-1 text-[12px]">
            {["阅读", "调查", "终局"].map((act, i) => (
              <span key={act} className="flex items-center gap-1">
                {i > 0 && <span className="text-smoke">▸</span>}
                <span
                  className={
                    i === 1
                      ? "text-acid-lime"
                      : i === 0
                        ? "text-fog"
                        : "text-fog"
                  }
                >
                  {act}
                </span>
              </span>
            ))}
          </nav>
          <span className="font-mono text-[11px] text-fog">剩余 2 调查点</span>
        </div>
        <div className="flex items-center gap-4 text-[13px] text-mist">
          <button className="transition-colors hover:text-paper">档案</button>
          <button className="transition-colors hover:text-paper">回看上一轮</button>
          <button className="text-ash transition-colors hover:text-coral-red">
            退出本局
          </button>
        </div>
      </header>

      {/* 主体：叙事流 + 档案抽屉 */}
      <div className="flex min-h-0 flex-1">
        <main className="flex-1 overflow-y-auto px-8 py-8">
          <div className="mx-auto max-w-2xl space-y-8">
            <Deposition
              n="#07"
              name="顾二"
              text="那天夜里我确实不在书房……我从晚饭后就一直在前院和车夫说话。"
            />
            <Deposition n="#08" name="你" text="那你当时在哪？" self />
            <Deposition
              n="#09"
              name="唐小姐"
              text="顾二在撒谎。晚饭后我见过他，就站在书房外头的回廊下。"
            />
          </div>
        </main>
        <aside className="hidden w-72 shrink-0 border-l border-graphite/60 bg-carbon/30 p-4 lg:block">
          <div className="font-mono text-[11px] tracking-widest text-fog">
            档案
          </div>
          <div className="mt-4 space-y-1 text-[13px] text-mist">
            {[
              "角色档案 · 4 人",
              "线索 · 证据（已解锁 7）",
              "回忆 · 3 条",
              "手记 · 我的笔记",
            ].map((item) => (
              <div
                key={item}
                className="cursor-pointer rounded-md px-2 py-1.5 transition-colors hover:bg-obsidian"
              >
                {item}
              </div>
            ))}
          </div>
        </aside>
      </div>

      {/* 底部 · 行动条 */}
      <footer className="shrink-0 border-t border-graphite/60 px-5 py-3">
        <div className="mx-auto flex max-w-2xl items-center gap-2">
          <button className="inline-flex items-center gap-1.5 rounded-md bg-acid-lime px-4 py-2 text-[14px] font-medium text-void transition-opacity hover:opacity-90">
            <Search size={15} strokeWidth={2} />
            调查书房
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-graphite px-4 py-2 text-[13px] text-mist transition-colors hover:border-smoke">
            <MessagesSquare size={15} strokeWidth={2} />
            公开讨论
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-graphite px-4 py-2 text-[13px] text-mist transition-colors hover:border-smoke">
            <Phone size={15} strokeWidth={2} />
            私聊唐小姐
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-md border border-graphite px-4 py-2 text-[13px] text-mist transition-colors hover:border-smoke">
            <HelpCircle size={15} strokeWidth={2} />
            提问
          </button>
        </div>
      </footer>
    </div>
  );
}

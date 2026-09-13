"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FileText, History, Play } from "lucide-react";
import { anonymousLogin, saveToken } from "@/services/auth";
import { listLibrary, listReleases } from "@/services/play";
import type { LibraryItem, Release } from "@/types/api";

export default function HomePage() {
  const [recent, setRecent] = useState<LibraryItem | null>(null);
  const [releases, setReleases] = useState<Release[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await anonymousLogin();
        saveToken(token);
        const [lib, rels] = await Promise.all([
          listLibrary(0, 1),
          listReleases(),
        ]);
        if (!cancelled) {
          setRecent(lib.items[0] ?? null);
          setReleases(rels);
        }
      } catch {
        // 离线：保持占位状态
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const hasScript = releases.length > 0;

  return (
    <div className="min-h-screen">
      {/* 顶栏 */}
      <header className="border-b border-graphite/60">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <div className="flex items-baseline gap-3">
            <span className="text-[15px] font-medium tracking-tight text-paper">
              人生海海
            </span>
            <span className="font-mono text-[11px] tracking-wide text-fog">
              1 HUMAN × AI · MURDER MYSTERY
            </span>
          </div>
          <nav className="flex items-center gap-6 text-[13px] text-mist">
            <Link href="/records" className="transition-colors hover:text-paper">
              我的记录
            </Link>
          </nav>
        </div>
      </header>

      {/* 主区 */}
      <main className="mx-auto max-w-5xl px-6 py-24">
        <p className="font-mono text-[12px] tracking-widest text-fog">
          {"// 单真人 AI 剧本杀"}
        </p>
        <h1 className="mt-5 max-w-2xl text-[44px] leading-[1.05] tracking-[-0.022em] text-paper">
          选一个角色，
          <br />
          其余交给 AI。
        </h1>
        <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-ash">
          你扮演凶手或侦探，其余角色由 AI 演绎。调查、盘问、投票，在深夜的案卷里走完一整局。
        </p>

        <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
          <Link
            href="/play"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-acid-lime px-4 py-2.5 text-[14px] font-medium tracking-[-0.011em] text-void transition-opacity hover:opacity-90"
          >
            <Play size={16} strokeWidth={2} />
            {hasScript ? "开始新游戏" : "进入游戏（离线演示）"}
          </Link>
          <Link
            href="/records"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-graphite px-4 py-2.5 text-[13px] text-mist transition-colors hover:border-smoke hover:text-paper"
          >
            <History size={15} strokeWidth={2} />
            我的记录
          </Link>
        </div>
      </main>

      {/* 最近一局 */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="rounded-lg bg-carbon p-6 shadow-subtle">
          <div className="flex items-center gap-2 text-[12px] text-fog">
            <FileText size={14} strokeWidth={2} />
            最近一局
          </div>
          {recent ? (
            <div className="mt-4 flex items-center justify-between">
              <div>
                <div className="text-[16px] font-medium text-paper">
                  {recent.title} · {recent.character_name}
                </div>
                <div className="mt-1 font-mono text-[12px] text-ash">
                  {recent.phase_label}
                  {recent.settled ? " · 已结束" : ""}
                </div>
              </div>
              <Link
                href={`/play?play_id=${recent.play_id}`}
                className="inline-flex items-center gap-1 text-[13px] text-acid-lime transition-opacity hover:opacity-80"
              >
                继续 <ArrowRight size={13} strokeWidth={2} />
              </Link>
            </div>
          ) : (
            <p className="mt-4 text-[13px] text-fog">
              还没有对局记录，点「开始新游戏」进入第一局。
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

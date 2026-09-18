"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, FileText, History, Play } from "lucide-react";
import { currentToken, ensureSession } from "@/services/auth";
import { listLibrary, listReleases } from "@/services/play";
import { errorCode } from "@/lib/http";
import type { LibraryItem, Release } from "@/types/api";

export default function HomePage() {
  const [recent, setRecent] = useState<LibraryItem | null>(null);
  const [releases, setReleases] = useState<Release[]>([]);
  const [loading, setLoading] = useState(true);
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [releaseError, setReleaseError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const requestVersion = useRef(0);
  const identityToken = useRef<string | null>(null);

  useEffect(() => {
    const version = ++requestVersion.current;
    (async () => {
      try {
        if (identityToken.current && !currentToken()) throw new Error("登录身份已变化，请重新登录后载入。");
        await ensureSession();
        if (requestVersion.current !== version) return;
        const token = currentToken();
        identityToken.current = token;
        const [lib, rels] = await Promise.allSettled([
          listLibrary(0, 1),
          listReleases(),
        ]);
        if (currentToken() !== token) throw new Error("登录身份已变化，请重新加载。");
        if (requestVersion.current === version) {
          if (lib.status === "fulfilled") setRecent(lib.value.items[0] ?? null);
          else setLibraryError(errorCode(lib.reason));
          if (rels.status === "fulfilled") setReleases(rels.value);
          else setReleaseError(errorCode(rels.reason));
        }
      } catch (error) {
        if (requestVersion.current === version) {
          setLibraryError(errorCode(error));
          setReleaseError(errorCode(error));
        }
      } finally {
        if (requestVersion.current === version) setLoading(false);
      }
    })();
    return () => {
      requestVersion.current += 1;
    };
  }, [refresh]);

  useEffect(() => {
    const checkIdentity = () => {
      if (!identityToken.current || currentToken() === identityToken.current) return;
      requestVersion.current += 1;
      setRecent(null);
      setReleases([]);
      setLoading(false);
      setLibraryError("登录身份已变化，请重新加载当前账号的记录。");
      setReleaseError("登录身份已变化，请重新加载。");
    };
    window.addEventListener("storage", checkIdentity);
    window.addEventListener("focus", checkIdentity);
    return () => {
      window.removeEventListener("storage", checkIdentity);
      window.removeEventListener("focus", checkIdentity);
    };
  }, []);

  function reload() {
    setLoading(true);
    setLibraryError(null);
    setReleaseError(null);
    setRefresh((value) => value + 1);
  }

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
            开始新游戏
          </Link>
          <Link
            href="/records"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-graphite px-4 py-2.5 text-[13px] text-mist transition-colors hover:border-smoke hover:text-paper"
          >
            <History size={15} strokeWidth={2} />
            我的记录
          </Link>
        </div>
        {!loading && releaseError ? (
          <div className="mt-4 text-[13px] text-ash" role="alert">
            <p>剧本列表加载失败：{releaseError}</p>
            <button type="button" onClick={reload} className="mt-2 text-acid-lime hover:underline">
              重新加载
            </button>
          </div>
        ) : !loading && releases.length === 0 ? (
          <p className="mt-4 text-[13px] text-ash">暂时没有可开始的剧本，请稍后再试。</p>
        ) : null}
      </main>

      {/* 最近一局 */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="rounded-lg bg-carbon p-6 shadow-subtle">
          <div className="flex items-center gap-2 text-[12px] text-fog">
            <FileText size={14} strokeWidth={2} />
            最近一局
          </div>
          {loading ? (
            <p className="mt-4 text-[13px] text-fog" role="status">正在读取最近一局…</p>
          ) : libraryError ? (
            <div className="mt-4 text-[13px] text-ash" role="alert">
              <p>记录加载失败：{libraryError}</p>
              <button type="button" onClick={reload} className="mt-2 text-acid-lime hover:underline">
                重新加载
              </button>
            </div>
          ) : recent ? (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0 break-words">
                <div className="text-[16px] font-medium text-paper">
                  {recent.title} · {recent.character_name}
                </div>
                <div className="mt-1 font-mono text-[12px] text-ash">
                  {recent.phase_label}
                  {recent.settled ? " · 已结束" : ""}
                </div>
              </div>
              <Link
                href={`/play?play_id=${encodeURIComponent(recent.play_id)}`}
                className="inline-flex shrink-0 items-center gap-1 text-[13px] text-acid-lime transition-opacity hover:opacity-80"
              >
                {recent.settled ? "查看结局" : "继续"} <ArrowRight size={13} strokeWidth={2} />
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

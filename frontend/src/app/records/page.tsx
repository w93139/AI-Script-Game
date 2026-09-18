"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { currentToken, ensureSession } from "@/services/auth";
import { listLibrary } from "@/services/play";
import { errorCode } from "@/lib/http";
import type { LibraryItem } from "@/types/api";

const PAGE_SIZE = 20;

export default function RecordsPage() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const requestVersion = useRef(0);
  const moreInFlight = useRef(false);
  const libraryToken = useRef<string | null>(null);

  useEffect(() => {
    const version = ++requestVersion.current;
    (async () => {
      try {
        if (libraryToken.current && !currentToken()) throw new Error("登录身份已变化，请重新登录后载入。");
        await ensureSession();
        if (requestVersion.current !== version) return;
        const token = currentToken();
        libraryToken.current = token;
        const lib = await listLibrary(0, PAGE_SIZE);
        if (currentToken() !== token) throw new Error("登录身份已变化，请重新加载。");
        if (requestVersion.current === version) {
          setItems(lib.items);
          setHasMore(lib.has_more);
          setNextOffset(lib.items.length);
        }
      } catch (failure) {
        if (requestVersion.current === version) setError(errorCode(failure));
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
      if (!libraryToken.current || currentToken() === libraryToken.current) return;
      requestVersion.current += 1;
      setItems([]);
      setHasMore(false);
      setNextOffset(0);
      setLoading(false);
      setLoadingMore(false);
      setError("登录身份已变化，请重新加载当前账号的记录。");
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
    setError(null);
    setRefresh((value) => value + 1);
  }

  async function loadMore() {
    if (loading || moreInFlight.current || !hasMore) return;
    moreInFlight.current = true;
    setLoadingMore(true);
    setError(null);
    const version = requestVersion.current;
    try {
      const token = currentToken();
      if (token !== libraryToken.current) throw new Error("登录身份已变化，请重新加载。");
      const lib = await listLibrary(nextOffset, PAGE_SIZE);
      if (currentToken() !== token) throw new Error("登录身份已变化，请重新加载。");
      if (requestVersion.current === version) {
        setItems((previous) => {
          const ids = new Set(previous.map((item) => item.play_id));
          return [...previous, ...lib.items.filter((item) => {
            if (ids.has(item.play_id)) return false;
            ids.add(item.play_id);
            return true;
          })];
        });
        setHasMore(lib.has_more);
        setNextOffset(nextOffset + lib.items.length);
      }
    } catch (failure) {
      if (requestVersion.current === version) setError(errorCode(failure));
    } finally {
      moreInFlight.current = false;
      if (requestVersion.current === version) setLoadingMore(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-20">
      <nav className="mb-8 flex items-center justify-between gap-4 text-[13px] text-mist">
        <Link href="/" className="transition-colors hover:text-paper">← 返回首页</Link>
        <Link href="/play" className="text-acid-lime transition-opacity hover:opacity-80">开始新游戏 →</Link>
      </nav>
      <p className="font-mono text-[12px] tracking-widest text-fog">
        {"// 我的记录"}
      </p>
      <h1 className="mt-4 text-[32px] tracking-[-0.022em] text-paper">
        历史对局
      </h1>

      {error && (
        <div className="mt-3 text-[14px] text-ash" role="alert">
          <p>记录加载失败：{error}</p>
          <button type="button" onClick={reload} disabled={loading || loadingMore} className="mt-2 text-acid-lime hover:underline disabled:opacity-50">
            重新加载
          </button>
        </div>
      )}

      {loading ? (
        <p className="mt-6 text-[14px] text-fog" role="status">加载中…</p>
      ) : items.length === 0 ? (
        !error && <p className="mt-6 text-[14px] text-ash">还没有对局记录。</p>
      ) : (
        <ul className="mt-6 space-y-2">
          {items.map((item) => (
            <li key={item.play_id}>
              <Link
                href={`/play?play_id=${encodeURIComponent(item.play_id)}`}
                className="flex items-center justify-between gap-4 rounded-lg border border-graphite/50 bg-carbon px-4 py-3 transition-colors hover:border-smoke"
              >
                <div className="min-w-0 break-words">
                  <div className="text-[14px] font-medium text-paper">
                    {item.title} · {item.character_name}
                  </div>
                  <div className="mt-0.5 font-mono text-[12px] text-ash">
                    {item.phase_label}{item.settled ? " · 已结束" : ""}
                  </div>
                </div>
                <div className="shrink-0 text-[13px] text-mist">
                  {item.settled ? "查看结局 →" : "继续 →"}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {!loading && hasMore && (
        <button
          type="button"
          onClick={loadMore}
          disabled={loadingMore}
          className="mt-6 rounded-md border border-graphite px-4 py-2.5 text-[13px] text-mist transition-colors hover:border-smoke hover:text-paper disabled:opacity-50"
        >
          {loadingMore ? "正在加载…" : error ? "重试加载更多" : "加载更多"}
        </button>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { anonymousLogin, saveToken } from "@/services/auth";
import { listLibrary } from "@/services/play";
import type { LibraryItem } from "@/types/api";

export default function RecordsPage() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await anonymousLogin();
        saveToken(token);
        const lib = await listLibrary(0, 50);
        if (!cancelled) setItems(lib.items);
      } catch {
        if (!cancelled) setOffline(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-6 py-20">
      <p className="font-mono text-[12px] tracking-widest text-fog">
        {"// 我的记录"}
      </p>
      <h1 className="mt-4 text-[32px] tracking-[-0.022em] text-paper">
        历史对局
      </h1>

      {offline && (
        <p className="mt-3 text-[14px] text-ash">
          离线演示：后端未连接，暂无历史记录。
        </p>
      )}

      {loading ? (
        <p className="mt-6 text-[14px] text-fog">加载中…</p>
      ) : items.length === 0 ? (
        <p className="mt-6 text-[14px] text-ash">还没有对局记录。</p>
      ) : (
        <ul className="mt-6 space-y-2">
          {items.map((item) => (
            <li key={item.play_id}>
              <Link
                href={`/play?play_id=${item.play_id}`}
                className="flex items-center justify-between rounded-lg border border-graphite/50 bg-carbon px-4 py-3 transition-colors hover:border-smoke"
              >
                <div>
                  <div className="text-[14px] font-medium text-paper">
                    {item.title} · {item.character_name}
                  </div>
                  <div className="mt-0.5 font-mono text-[12px] text-ash">
                    {item.phase_label}
                  </div>
                </div>
                <div className="text-[13px] text-mist">
                  {item.settled ? "已结束" : "继续 →"}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

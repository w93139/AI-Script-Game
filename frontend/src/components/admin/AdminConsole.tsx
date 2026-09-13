"use client";

import { useEffect, useState } from "react";
import { listReleases } from "@/services/play";
import {
  listAuthoringJobs,
  listReviewCandidates,
  listSourceBundles,
} from "@/services/admin";

type SectionId = "import" | "authoring" | "review" | "publish" | "sources";

interface Section {
  id: SectionId;
  label: string;
  desc: string;
  fetcher?: () => Promise<unknown[]>;
}

const SECTIONS: Section[] = [
  {
    id: "import",
    label: "剧本导入",
    desc: "导入候选包，进入编译与审核流程。",
  },
  {
    id: "authoring",
    label: "编译任务",
    desc: "排队、取消编译与模型审核任务。",
    fetcher: listAuthoringJobs,
  },
  {
    id: "review",
    label: "审核候选",
    desc: "人工审核与问题处理记录。",
    fetcher: listReviewCandidates,
  },
  {
    id: "publish",
    label: "剧本发布",
    desc: "版本确认、审批与发布登记。",
    fetcher: listReleases,
  },
  {
    id: "sources",
    label: "来源核验",
    desc: "私有来源文件快照与一致性核对。",
    fetcher: listSourceBundles,
  },
];

function SectionPanel({ section }: { section: Section }) {
  const [status, setStatus] = useState<"loading" | "ok" | "error">(
    section.fetcher ? "loading" : "ok",
  );
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    if (!section.fetcher) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await section.fetcher!();
        if (!cancelled) {
          setCount(Array.isArray(data) ? data.length : null);
          setStatus("ok");
        }
      } catch {
        if (!cancelled) setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [section]);

  return (
    <div>
      <h2 className="text-[20px] tracking-[-0.012em] text-paper">
        {section.label}
      </h2>
      <p className="mt-2 text-[14px] leading-relaxed text-ash">{section.desc}</p>

      <div className="mt-6 rounded-lg border border-graphite/60 bg-carbon p-5">
        {status === "loading" && (
          <p className="text-[13px] text-fog">加载中…</p>
        )}
        {status === "error" && (
          <p className="text-[13px] text-ash">
            后端未连接或当前账号无管理权限——接入后显示数据。
          </p>
        )}
        {status === "ok" &&
          (count !== null ? (
            <p className="font-mono text-[13px] text-mist">{count} 项</p>
          ) : (
            <p className="text-[13px] text-ash">该环节由操作触发，暂无列表。</p>
          ))}
      </div>
    </div>
  );
}

export default function AdminConsole() {
  const [active, setActive] = useState<SectionId>("authoring");
  const section = SECTIONS.find((s) => s.id === active) ?? SECTIONS[0];

  return (
    <div className="flex min-h-screen">
      {/* 侧栏 */}
      <aside className="w-56 shrink-0 border-r border-graphite/60 bg-carbon/30">
        <div className="border-b border-graphite/60 px-4 py-4">
          <span className="text-[14px] font-medium text-paper">剧本工作台</span>
          <span className="mt-1 block font-mono text-[11px] text-fog">
            ADMIN CONSOLE
          </span>
        </div>
        <nav className="space-y-1 p-2">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              onClick={() => setActive(s.id)}
              className={
                s.id === active
                  ? "w-full rounded-md bg-obsidian px-3 py-2 text-left text-[13px] text-paper"
                  : "w-full rounded-md px-3 py-2 text-left text-[13px] text-fog transition-colors hover:text-mist"
              }
            >
              {s.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* 内容 */}
      <main className="flex-1 px-10 py-10">
        <div className="max-w-2xl">
          <SectionPanel key={section.id} section={section} />
        </div>
      </main>
    </div>
  );
}

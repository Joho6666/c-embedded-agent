"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { KnowledgeCard } from "@/components/knowledge/KnowledgeCard";
import { Empty } from "@/components/common/Empty";
import { knowledgeDocs } from "@/lib/mock/knowledge";
import type { KnowledgeDocument } from "@/types/knowledge";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { useLive } from "@/lib/stores/live-store";
import { API_BASE } from "@/lib/api/client";

const cats: Array<{ id: KnowledgeDocument["category"] | "All"; label: string }> = [
  { id: "All", label: "全部" },
  { id: "STM32", label: "STM32" },
  { id: "ESP32", label: "ESP32" },
  { id: "C Language", label: "C 语言" },
  { id: "RTOS", label: "RTOS" },
];

export default function KnowledgePage() {
  const [cat, setCat] = useState<(typeof cats)[number]["id"]>("All");
  const [q, setQ] = useState("");
  const [liveHits, setLiveHits] = useState<string>("");
  const mode = useLive((s) => s.mode);
  const open = useWorkspaceUI((s) => s.setKnowledgeId);

  useEffect(() => {
    if (mode !== "live" || !q.trim()) {
      setLiveHits("");
      return;
    }
    const t = window.setTimeout(() => {
      void fetch(`${API_BASE}/api/knowledge?q=${encodeURIComponent(q)}`)
        .then((r) => r.json())
        .then((rows: Array<{ title: string; excerpt: string }>) => {
          setLiveHits(rows.map((x) => `${x.title}: ${x.excerpt.slice(0, 80)}`).join("\n"));
        })
        .catch(() => setLiveHits(""));
    }, 300);
    return () => window.clearTimeout(t);
  }, [mode, q]);
  const docs = useMemo(() => {
    return knowledgeDocs.filter((d) => {
      const okCat = cat === "All" || d.category === cat;
      const s = q.trim().toLowerCase();
      const okQ =
        !s ||
        d.title.toLowerCase().includes(s) ||
        (d.subtitle ?? "").toLowerCase().includes(s) ||
        d.vendor.toLowerCase().includes(s);
      return okCat && okQ;
    });
  }, [cat, q]);

  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">Knowledge</h1>
      <p className="text-[12px] text-muted-foreground">
        Datasheet · HAL · Skills · Error Memory
        {mode === "live" ? " · LIVE 检索后端知识库" : " · DEMO 本地目录"}
      </p>
      <div className="mt-2 flex gap-2 text-[12px]">
        <Link className="text-primary" href="/skills">
          Skills
        </Link>
        <Link className="text-primary" href="/memory/errors">
          Error Memory
        </Link>
      </div>
      {liveHits && <pre className="mt-2 max-w-xl whitespace-pre-wrap rounded-sm border border-border bg-panel-2 p-2 text-[11px] text-muted-foreground">{liveHits}</pre>}
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="搜索 RM0008 / HAL / Datasheet…"
        className="mt-3 h-8 w-full max-w-md rounded-sm border border-input bg-panel-2 px-2 text-[12px] outline-none"
      />
      <div className="mt-3 flex gap-1">
        {cats.map((c) => (
          <button
            key={c.id}
            onClick={() => setCat(c.id)}
            className={`rounded-sm px-2 py-1 text-[12px] ${cat === c.id ? "bg-accent" : "text-muted-foreground"}`}
          >
            {c.label}
          </button>
        ))}
      </div>
      {docs.length === 0 ? (
        <div className="mt-6">
          <Empty title="无匹配文档" hint="换一个关键词或分类" />
        </div>
      ) : (
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {docs.map((d) => (
            <KnowledgeCard key={d.id} doc={d} onOpen={() => open(d.id)} />
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { KnowledgeCard } from "@/components/knowledge/KnowledgeCard";
import { Button } from "@/components/ui/button";
import { knowledgeDocs } from "@/lib/mock/knowledge";
import type { KnowledgeDoc } from "@/types/knowledge";

const cats: Array<KnowledgeDoc["category"] | "All"> = ["All", "STM32", "ESP32", "C Language", "RTOS"];

export default function KnowledgePage() {
  const [cat, setCat] = useState<(typeof cats)[number]>("All");
  const docs = useMemo(
    () => (cat === "All" ? knowledgeDocs : knowledgeDocs.filter((d) => d.category === cat)),
    [cat],
  );

  return (
    <div className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-[18px] font-semibold">Embedded Knowledge Base</h1>
          <p className="text-[12px] text-muted-foreground">Datasheet · HAL · MISRA · RTOS</p>
        </div>
        <div className="flex flex-wrap gap-1">
          <Button size="sm" variant="outline">上传 PDF</Button>
          <Button size="sm" variant="outline">上传 Datasheet</Button>
          <Button size="sm" variant="outline">GitHub 导入</Button>
          <Button size="sm" variant="outline">URL 导入</Button>
        </div>
      </div>
      <div className="mt-4 flex gap-1">
        {cats.map((c) => (
          <button
            key={c}
            onClick={() => setCat(c)}
            className={`rounded-sm px-2 py-1 text-[12px] ${cat === c ? "bg-accent" : "text-muted-foreground"}`}
          >
            {c}
          </button>
        ))}
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {docs.map((d) => (
          <KnowledgeCard key={d.id} doc={d} />
        ))}
      </div>
    </div>
  );
}

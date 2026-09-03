"use client";

import { useEffect, useState } from "react";
import { ErrorMemoryList } from "@/components/memory/ErrorMemoryList";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { Empty } from "@/components/common/Empty";
import { listErrorMemories } from "@/lib/api/memory";
import type { ErrorMemoryEntry, ErrorMemoryTag } from "@/types/memory";
import { useLive } from "@/lib/stores/live-store";

const tags: Array<ErrorMemoryTag | "all"> = ["all", "Compiler", "Linker", "HAL", "GPIO", "Clock", "UART", "DMA"];

export default function ErrorMemoryPage() {
  const mode = useLive((s) => s.mode);
  const [q, setQ] = useState("");
  const [tag, setTag] = useState<(typeof tags)[number]>("all");
  const [items, setItems] = useState<ErrorMemoryEntry[]>([]);
  const [reason, setReason] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "live") {
      setReason("Backend capability unavailable");
      setItems([]);
      return;
    }
    void listErrorMemories(q, tag).then((r) => {
      setItems(r.items);
      setReason(r.available ? null : r.reason ?? "Backend Not Implemented");
    });
  }, [mode, q, tag]);

  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">Error Memory</h1>
      <p className="text-[12px] text-muted-foreground">Agent 曾经成功解决的真实错误。空列表合法，不伪造成功率。</p>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search Errors"
        className="mt-3 h-8 w-full max-w-md rounded-sm border border-input bg-panel-2 px-2 text-[12px] outline-none"
      />
      <div className="mt-3 flex flex-wrap gap-1">
        {tags.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTag(t)}
            className={`rounded-sm px-2 py-1 text-[12px] ${tag === t ? "bg-accent" : "text-muted-foreground"}`}
          >
            {t === "all" ? "All" : t}
          </button>
        ))}
      </div>
      {reason && <div className="mt-3"><CapabilityBanner reason={reason} /></div>}
      <div className="mt-4">
        {!reason && items.length === 0 ? <Empty title="尚无已验证修复" hint="编译错误命中模板后才会累计 Occurrences" /> : null}
        {items.length > 0 ? <ErrorMemoryList items={items} /> : null}
      </div>
    </div>
  );
}

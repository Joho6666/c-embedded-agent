"use client";

import { useEffect, useRef } from "react";
import type { SerialLine } from "@/types/debug";

export function SerialMonitor({
  lines,
  port = "COM3",
  baud = 115200,
}: {
  lines: SerialLine[];
  port?: string;
  baud?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines]);
  return (
    <div className="flex h-full flex-col bg-terminal">
      <div className="flex items-center gap-2 border-b border-border px-3 py-1.5 text-[11px] text-muted-foreground">
        <span className="text-success">●</span>
        {port} · {baud} baud · 已连接
      </div>
      <div ref={ref} className="terminal flex-1 overflow-auto px-3 py-2 text-[12px] leading-5">
        {lines.length === 0 && <div className="text-muted-foreground">等待串口数据…</div>}
        {lines.map((l, i) => (
          <div key={`${l.ts}-${i}`}>
            <span className="text-muted-foreground">[{l.ts}]</span> <span className="text-zinc-200">{l.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

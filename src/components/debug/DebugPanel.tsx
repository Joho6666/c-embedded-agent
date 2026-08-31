"use client";

import { callStack, registers, watches } from "@/lib/mock/build";

export function DebugPanel() {
  return (
    <div className="grid h-full grid-cols-3 gap-px bg-border text-[12px]">
      <section className="overflow-auto bg-panel p-3">
        <h3 className="mb-2 text-[11px] font-medium text-muted-foreground">寄存器</h3>
        {registers.map((r) => (
          <div key={r.name} className="flex justify-between font-mono">
            <span className="text-muted-foreground">{r.name}</span>
            <span>{r.value}</span>
          </div>
        ))}
      </section>
      <section className="overflow-auto bg-panel p-3">
        <h3 className="mb-2 text-[11px] font-medium text-muted-foreground">调用栈</h3>
        {callStack.map((f) => (
          <div key={f.name} className="mb-1">
            <div className="font-mono">{f.name}</div>
            <div className="text-[11px] text-muted-foreground">{f.location}</div>
          </div>
        ))}
      </section>
      <section className="overflow-auto bg-panel p-3">
        <h3 className="mb-2 text-[11px] font-medium text-muted-foreground">监视</h3>
        {watches.map((w) => (
          <div key={w.name} className="flex justify-between font-mono">
            <span className="text-info">{w.name}</span>
            <span>{w.value}</span>
          </div>
        ))}
      </section>
    </div>
  );
}

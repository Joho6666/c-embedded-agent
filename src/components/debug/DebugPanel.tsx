"use client";

import { callStack, registers, watches } from "@/lib/mock/build";

export function DebugPanel() {
  return (
    <div className="grid h-full grid-cols-3 gap-px bg-border text-[12px]">
      <section className="overflow-auto bg-panel p-3">
        <h3 className="mb-2 text-[11px] font-medium text-muted-foreground">Registers</h3>
        <div className="space-y-1 font-mono">
          {registers.map((r) => (
            <div key={r.name} className="flex justify-between">
              <span className="text-muted-foreground">{r.name}</span>
              <span>{r.value}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="overflow-auto bg-panel p-3">
        <h3 className="mb-2 text-[11px] font-medium text-muted-foreground">Call Stack</h3>
        <ol className="space-y-1.5">
          {callStack.map((f) => (
            <li key={f.name}>
              <div className="font-mono">{f.name}</div>
              <div className="text-[11px] text-muted-foreground">{f.location}</div>
            </li>
          ))}
        </ol>
      </section>
      <section className="overflow-auto bg-panel p-3">
        <h3 className="mb-2 text-[11px] font-medium text-muted-foreground">Watch</h3>
        <div className="space-y-1 font-mono">
          {watches.map((w) => (
            <div key={w.name} className="flex justify-between">
              <span className="text-info">{w.name}</span>
              <span>{w.value}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

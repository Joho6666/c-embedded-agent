"use client";

import { SerialMonitor } from "@/components/terminal/SerialMonitor";
import { serialLog } from "@/lib/mock/build";
import { useTerminal } from "@/lib/stores/terminal-store";

export default function SerialPage() {
  const live = useTerminal((s) => s.serialLines);
  return (
    <div className="flex h-full flex-col p-5">
      <h1 className="mb-3 text-[18px] font-semibold">串口监视器</h1>
      <p className="mb-3 text-[12px] text-muted-foreground">COM3 · 115200 baud</p>
      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-border">
        <SerialMonitor lines={live.length ? live : serialLog} />
      </div>
    </div>
  );
}

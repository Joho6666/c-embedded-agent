"use client";

import { DebugPanel } from "@/components/debug/DebugPanel";

export default function DebugPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-5 py-3">
        <h1 className="text-[18px] font-semibold">Debug</h1>
        <p className="text-[12px] text-muted-foreground">Registers · Call Stack · Watch</p>
      </div>
      <div className="min-h-0 flex-1">
        <DebugPanel />
      </div>
    </div>
  );
}

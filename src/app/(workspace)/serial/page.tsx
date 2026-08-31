"use client";

import { SerialMonitor } from "@/components/terminal/SerialMonitor";
import { serialLog } from "@/lib/mock/build";
import { useWorkspace } from "@/lib/stores/workspace";
import { Button } from "@/components/ui/button";

export default function SerialPage() {
  const live = useWorkspace((s) => s.serialLines);
  const lines = live.length ? live : serialLog;
  return (
    <div className="flex h-full flex-col p-5">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold">Serial Monitor</h1>
          <p className="text-[12px] text-muted-foreground">COM3 · 115200 baud</p>
        </div>
        <Button variant="outline">Connect</Button>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden rounded-sm border border-border">
        <SerialMonitor lines={lines} />
      </div>
    </div>
  );
}

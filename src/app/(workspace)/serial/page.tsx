"use client";

import { SerialMonitor } from "@/components/hardware/SerialMonitor";

export default function SerialPage() {
  return (
    <div className="flex h-full flex-col p-5">
      <h1 className="mb-3 text-[18px] font-semibold">串口监视器</h1>
      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-border">
        <SerialMonitor />
      </div>
    </div>
  );
}

"use client";

import { useHardware } from "@/lib/stores/hardware-store";
import { useAgent } from "@/lib/stores/agent-store";
import { agentStatusLabel } from "@/lib/i18n";

export function StatusBar() {
  const ctx = useHardware((s) => s.context);
  const status = useAgent((s) => s.status);
  return (
    <footer className="flex h-6 shrink-0 items-center gap-3 border-t border-border bg-chrome px-3 font-mono text-[10px] text-muted-foreground">
      <span>main*</span>
      <span>UTF-8</span>
      <span>LF</span>
      <span>C</span>
      <span>{ctx.mcu || "MCU unknown"}</span>
      <span>{ctx.clock || "clock unknown"}</span>
      <span>{ctx.serialPort ? `${ctx.serialPort} · ${ctx.serialBaud || "—"}` : "serial unknown"}</span>
      <span className="ml-auto">C-Agent: {agentStatusLabel(status)}</span>
    </footer>
  );
}

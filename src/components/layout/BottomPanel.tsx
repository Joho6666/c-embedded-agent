"use client";

import { Terminal } from "@/components/terminal/Terminal";
import { SerialMonitor } from "@/components/hardware/SerialMonitor";
import { ProblemList } from "@/components/problems/ProblemList";
import { useTerminal } from "@/lib/stores/terminal-store";
import { useWorkspaceUI, type BottomTab } from "@/lib/stores/workspace-store";
import { cn } from "@/lib/utils";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { useLive } from "@/lib/stores/live-store";

const tabs: { id: BottomTab; label: string }[] = [
  { id: "problems", label: "PROBLEMS" },
  { id: "output", label: "OUTPUT" },
  { id: "terminal", label: "TERMINAL" },
  { id: "serial", label: "SERIAL" },
];

export function BottomPanel() {
  const tab = useWorkspaceUI((s) => s.bottomTab);
  const setTab = useWorkspaceUI((s) => s.setBottomTab);
  const open = useWorkspaceUI((s) => s.bottomOpen);
  const toggle = useWorkspaceUI((s) => s.toggleBottom);
  const terminalLines = useTerminal((s) => s.terminalLines);
  const buildLines = useTerminal((s) => s.buildLines);
  const serialLines = useTerminal((s) => s.serialLines);
  const mode = useLive((s) => s.mode);

  const effective = tab === "build" || tab === "debug" ? "terminal" : tab;

  return (
    <div className="flex h-full flex-col bg-panel">
      <div className="flex h-8 shrink-0 items-center border-b border-border bg-chrome px-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "h-8 px-2.5 text-[11px] tracking-wide",
              effective === t.id ? "border-b-2 border-primary text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
        <button onClick={toggle} className="ml-auto px-2 text-[11px] text-muted-foreground hover:text-foreground">
          {open ? "隐藏" : "显示"}
        </button>
      </div>
      <div className="min-h-0 flex-1">
        {effective === "problems" && <ProblemList />}
        {effective === "output" && <Terminal lines={buildLines.length ? buildLines : terminalLines} />}
        {effective === "terminal" && <Terminal lines={terminalLines} />}
        {effective === "serial" &&
          (mode === "live" ? (
            <SerialMonitor />
          ) : (
            <div className="p-3">
              <CapabilityBanner reason="串口需要 LIVE 后端。当前未连接，不会显示假 Connected。" />
              <Terminal lines={serialLines.map((l) => `[${l.ts}] ${l.text}`)} />
            </div>
          ))}
      </div>
    </div>
  );
}

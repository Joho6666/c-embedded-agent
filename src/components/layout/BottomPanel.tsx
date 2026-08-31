"use client";

import { Terminal } from "@/components/terminal/Terminal";
import { SerialMonitor } from "@/components/terminal/SerialMonitor";
import { ProblemList } from "@/components/problems/ProblemList";
import { DebugPanel } from "@/components/debug/DebugPanel";
import { latestBuild } from "@/lib/mock/build";
import { useWorkspace, type BottomTab } from "@/lib/stores/workspace";
import { cn } from "@/lib/utils";

const tabs: { id: BottomTab; label: string }[] = [
  { id: "terminal", label: "Terminal" },
  { id: "build", label: "Build" },
  { id: "problems", label: "Problems" },
  { id: "serial", label: "Serial" },
  { id: "debug", label: "Debug" },
];

export function BottomPanel() {
  const tab = useWorkspace((s) => s.bottomTab);
  const setTab = useWorkspace((s) => s.setBottomTab);
  const open = useWorkspace((s) => s.bottomOpen);
  const toggle = useWorkspace((s) => s.toggleBottom);
  const terminalLines = useWorkspace((s) => s.terminalLines);
  const serialLines = useWorkspace((s) => s.serialLines);

  return (
    <div className="flex h-full flex-col bg-panel">
      <div className="flex h-7 shrink-0 items-center border-b border-border bg-chrome px-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "h-7 px-2.5 text-[11px]",
              tab === t.id ? "border-b border-primary text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
        <button onClick={toggle} className="ml-auto px-2 text-[11px] text-muted-foreground">
          {open ? "隐藏" : "显示"} ⌃
        </button>
      </div>
      <div className="min-h-0 flex-1">
        {tab === "terminal" && <Terminal lines={terminalLines} />}
        {tab === "build" && <Terminal lines={latestBuild.output} />}
        {tab === "problems" && <ProblemList />}
        {tab === "serial" && <SerialMonitor lines={serialLines} />}
        {tab === "debug" && <DebugPanel />}
      </div>
    </div>
  );
}

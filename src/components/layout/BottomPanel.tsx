"use client";

import { Terminal } from "@/components/terminal/Terminal";
import { SerialMonitor } from "@/components/terminal/SerialMonitor";
import { ProblemList } from "@/components/problems/ProblemList";
import { DebugPanel } from "@/components/debug/DebugPanel";
import { latestBuild } from "@/lib/mock/build";
import { useTerminal } from "@/lib/stores/terminal-store";
import { useWorkspaceUI, type BottomTab } from "@/lib/stores/workspace-store";
import { cn } from "@/lib/utils";

const tabs: { id: BottomTab; label: string }[] = [
  { id: "terminal", label: "终端" },
  { id: "build", label: "构建" },
  { id: "problems", label: "问题" },
  { id: "serial", label: "串口" },
  { id: "debug", label: "调试" },
];

export function BottomPanel() {
  const tab = useWorkspaceUI((s) => s.bottomTab);
  const setTab = useWorkspaceUI((s) => s.setBottomTab);
  const open = useWorkspaceUI((s) => s.bottomOpen);
  const toggle = useWorkspaceUI((s) => s.toggleBottom);
  const terminalLines = useTerminal((s) => s.terminalLines);
  const buildLines = useTerminal((s) => s.buildLines);
  const serialLines = useTerminal((s) => s.serialLines);

  return (
    <div className="flex h-full flex-col bg-panel">
      <div className="flex h-8 shrink-0 items-center border-b border-border bg-chrome px-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "h-8 px-2.5 text-[12px]",
              tab === t.id ? "border-b-2 border-primary text-foreground" : "text-muted-foreground hover:text-foreground",
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
        {tab === "terminal" && <Terminal lines={terminalLines} />}
        {tab === "build" && <Terminal lines={buildLines.length ? buildLines : latestBuild.output} />}
        {tab === "problems" && <ProblemList />}
        {tab === "serial" && <SerialMonitor lines={serialLines} />}
        {tab === "debug" && <DebugPanel />}
      </div>
    </div>
  );
}

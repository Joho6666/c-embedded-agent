"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bug, Cpu, GitBranch, Hammer, Play, Settings, Square, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAgent } from "@/lib/stores/agent-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { useProject, currentProject } from "@/lib/stores/project-store";
import { useTerminal } from "@/lib/stores/terminal-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { agentStatusLabel } from "@/lib/i18n";
import { useLive } from "@/lib/stores/live-store";
import { compileProject } from "@/lib/api/build";
import { cn } from "@/lib/utils";
import { useEffect } from "react";

export function TopBar() {
  const router = useRouter();
  const status = useAgent((s) => s.status);
  const statusText = useAgent((s) => s.statusText);
  const waiting = status === "waiting_approval";
  const startGoldenPath = useAgent((s) => s.startGoldenPath);
  const stopRun = useAgent((s) => s.stopRun);
  const mcu = useHardware((s) => s.context.mcu);
  const setBottomTab = useWorkspaceUI((s) => s.setBottomTab);
  const appendTerminal = useTerminal((s) => s.appendTerminal);
  const projectId = useProject((s) => s.projectId);
  const project = currentProject();
  const liveMode = useLive((s) => s.mode);
  const refreshLive = useLive((s) => s.refresh);
  void projectId;
  useEffect(() => {
    void refreshLive();
    const t = window.setInterval(() => void refreshLive(), 15000);
    return () => window.clearInterval(t);
  }, [refreshLive]);

  return (
    <header className="flex h-11 shrink-0 items-center gap-3 border-b border-border bg-chrome px-3">
      <Link href="/" className="flex items-center gap-2 pr-2">
        <span className="flex size-6 items-center justify-center rounded-sm bg-primary text-[11px] font-bold text-primary-foreground shadow-[0_0_0_1px_rgba(59,130,246,0.35)]">
          C
        </span>
        <span className="hidden text-[13px] font-semibold tracking-tight lg:inline">C-Embedded Agent</span>
        <span
          className={cn(
            "rounded-sm px-1.5 py-0.5 text-[10px] font-medium",
            liveMode === "live" && "bg-success/15 text-success",
            liveMode === "demo" && "bg-warning/15 text-warning",
            liveMode === "offline" && "bg-error/15 text-error",
          )}
        >
          {liveMode === "live" ? "LIVE" : liveMode === "offline" ? "后端离线" : "DEMO"}
        </span>
      </Link>
      <div className="hidden items-center gap-2 text-[11px] text-muted-foreground md:flex">
        <span className="rounded-sm border border-border bg-panel px-1.5 py-0.5 text-foreground">{project.name}</span>
        <span className="inline-flex items-center gap-1">
          <Cpu className="size-3" />
          {mcu}
        </span>
        <span className="inline-flex items-center gap-1">
          <GitBranch className="size-3" />
          {project.gitBranch}
        </span>
      </div>
      <div className="mx-auto flex min-w-0 items-center gap-2 text-[12px]">
        <span
          className={cn(
            "size-1.5 rounded-full",
            status === "working" && "pulse-dot bg-info",
            waiting && "pulse-dot bg-warning",
            status === "ready" && "bg-success",
            status === "error" && "bg-error",
            status === "stopped" && "bg-warning",
          )}
        />
        <span className="truncate font-medium">{agentStatusLabel(status)}</span>
        {(status === "working" || waiting) && (
          <span className="hidden truncate text-muted-foreground sm:inline">{statusText}</span>
        )}
      </div>
      <div className="ml-auto flex items-center gap-1">
        <Button
          onClick={() => {
            setBottomTab("build");
            if (liveMode !== "live") {
              appendTerminal(["Backend capability unavailable"]);
              return;
            }
            appendTerminal([`$ make -j4  (${projectId})`]);
            void compileProject(projectId).then((r) => {
              if (r.combined) appendTerminal(r.combined.split("\n").slice(-40));
              appendTerminal([r.success ? "exit 0" : `build failed ${r.error ?? r.exit_code ?? ""}`.trim()]);
            });
          }}
          title="Ctrl+B"
        >
          <Hammer />
          构建
        </Button>
        <Button
          variant="success"
          onClick={() => {
            void startGoldenPath();
            router.push("/agent");
          }}
        >
          <Play />
          运行
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            setBottomTab("terminal");
            appendTerminal(["$ STM32_Programmer_CLI -c port=SWD"]);
          }}
        >
          <Upload />
          烧录
        </Button>
        <Button variant="outline" onClick={() => router.push("/debug")}>
          <Bug />
          调试
        </Button>
        <Button variant="destructive" disabled={status !== "working" && !waiting} onClick={() => void stopRun()}>
          <Square />
          停止
        </Button>
        <Button variant="ghost" size="icon" asChild>
          <Link href="/settings">
            <Settings />
          </Link>
        </Button>
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bug, Cpu, GitBranch, Hammer, MoreHorizontal, Play, Square, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { useAgent } from "@/lib/stores/agent-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { useProject, currentProject } from "@/lib/stores/project-store";
import { useTerminal } from "@/lib/stores/terminal-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { useLive } from "@/lib/stores/live-store";
import { compileProject } from "@/lib/api/build";
import { flashProject } from "@/lib/api/flash";
import { agentStatusLabel } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { getPlatform, normalizePlatformId } from "@/lib/platform";
import { actionLabel, disabledReason } from "@/lib/platform/capabilities";
import type { ToolbarActionId } from "@/types/platform";
import { useEffect, type ReactNode } from "react";

export function ToolBar() {
  const router = useRouter();
  const status = useAgent((s) => s.status);
  const statusText = useAgent((s) => s.statusText);
  const waiting = status === "waiting_approval";
  const startGoldenPath = useAgent((s) => s.startGoldenPath);
  const stopRun = useAgent((s) => s.stopRun);
  const hw = useHardware((s) => s.context);
  const setBottomTab = useWorkspaceUI((s) => s.setBottomTab);
  const appendTerminal = useTerminal((s) => s.appendTerminal);
  const projectId = useProject((s) => s.projectId);
  const project = currentProject();
  const liveMode = useLive((s) => s.mode);
  const refreshLive = useLive((s) => s.refresh);

  const platform = getPlatform(normalizePlatformId(hw.platform || project.platformId || project.platform));

  useEffect(() => {
    void refreshLive();
    const t = window.setInterval(() => void refreshLive(), 15000);
    return () => window.clearInterval(t);
  }, [refreshLive]);

  const reason = (action: ToolbarActionId) => disabledReason(platform, action, liveMode);

  const runBuild = () => {
    setBottomTab("terminal");
    const why = reason("build");
    if (why) {
      appendTerminal([why]);
      return;
    }
    appendTerminal([`$ make -j4  (${projectId})`]);
    void compileProject(projectId).then((r) => {
      if (r.combined) appendTerminal(r.combined.split("\n").slice(-40));
      appendTerminal([r.success ? "exit 0" : `build failed ${r.error ?? r.exit_code ?? ""}`.trim()]);
    });
  };

  const runFlash = () => {
    setBottomTab("terminal");
    const why = reason("flash");
    if (why) {
      appendTerminal([why]);
      return;
    }
    appendTerminal([`$ openocd  program firmware.elf verify reset  (${projectId})`]);
    void flashProject(projectId).then((r) => {
      if (r.log) appendTerminal(r.log.split("\n").slice(-40));
      appendTerminal([r.ok ? "flash ok" : `flash failed ${r.error ?? ""}`.trim()]);
    });
  };

  const actions: Array<{
    id: ToolbarActionId;
    icon: typeof Hammer;
    variant: "default" | "success" | "secondary" | "outline" | "destructive";
    run: () => void;
    extraDisabled?: boolean;
  }> = [
    { id: "build", icon: Hammer, variant: "default", run: runBuild },
    {
      id: "run",
      icon: Play,
      variant: "success",
      run: () => {
        const why = reason("run");
        if (why) {
          appendTerminal([why]);
          return;
        }
        void startGoldenPath();
        router.push("/workspace");
      },
    },
    { id: "flash", icon: Upload, variant: "secondary", run: runFlash },
    {
      id: "debug",
      icon: Bug,
      variant: "outline",
      run: () => router.push("/debug"),
    },
    {
      id: "stop",
      icon: Square,
      variant: "destructive",
      run: () => void stopRun(),
      extraDisabled: status !== "working" && !waiting,
    },
  ];

  return (
    <header className="flex h-11 shrink-0 items-center gap-2 border-b border-border bg-chrome px-2">
      <Link href="/" className="flex items-center gap-2 pr-2">
        <span className="flex size-6 items-center justify-center rounded-sm bg-primary text-[11px] font-bold text-primary-foreground">
          C
        </span>
        <span className="hidden leading-tight lg:block">
          <span className="block text-[13px] font-semibold tracking-tight">C-Agent Workbench 2.0</span>
          <span className="block text-[10px] text-muted-foreground">AI 驱动的嵌入式 C 开发环境</span>
        </span>
      </Link>
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

      <div className="hidden h-7 items-center gap-1 border-l border-border pl-2 text-[11px] md:flex">
        <Field label="项目" value={project.name} />
        <Field label="平台" value={platform.label} icon={<Cpu className="size-3" />} />
        <Field label="分支" value={project.gitBranch || "main"} icon={<GitBranch className="size-3" />} />
        <Field
          label="设备"
          value={hw.debugger || "Probe status unknown"}
          tone={hw.debugger ? "success" : "muted"}
        />
      </div>

      <div className="mx-auto hidden min-w-0 items-center gap-2 text-[12px] xl:flex">
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
          <span className="hidden truncate text-muted-foreground 2xl:inline">{statusText}</span>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1">
        {actions.map((a) => {
            const why = a.id === "stop" ? null : reason(a.id);
            const disabled = Boolean(why) || Boolean(a.extraDisabled);
            const btn = (
              <Button
                key={a.id}
                variant={a.variant}
                disabled={disabled}
                onClick={a.run}
                title={why ?? actionLabel(a.id)}
              >
                <a.icon />
                {actionLabel(a.id)}
              </Button>
            );
            return why ? (
              <Tooltip key={a.id} content={why}>
                <span className="inline-flex">{btn}</span>
              </Tooltip>
            ) : (
              btn
            );
          })}
        <Button variant="ghost" size="icon" asChild>
          <Link href="/settings" title="更多">
            <MoreHorizontal />
          </Link>
        </Button>
      </div>
    </header>
  );
}

function Field({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: string;
  icon?: ReactNode;
  tone?: "success" | "muted";
}) {
  return (
    <div className="flex items-center gap-1 rounded-sm border border-border bg-panel px-1.5 py-0.5">
      <span className="text-muted-foreground">{label}</span>
      {icon}
      {tone === "success" && <span className="size-1.5 rounded-full bg-success" />}
      <span className="max-w-[140px] truncate text-foreground">{value}</span>
    </div>
  );
}

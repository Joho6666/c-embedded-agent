"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bug,
  Cpu,
  GitBranch,
  Play,
  Settings,
  Square,
  Upload,
  Hammer,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/lib/stores/workspace";
import { projects } from "@/lib/mock/projects";
import { cn } from "@/lib/utils";

export function TopBar() {
  const router = useRouter();
  const agentStatus = useWorkspace((s) => s.agentStatus);
  const statusText = useWorkspace((s) => s.statusText);
  const running = useWorkspace((s) => s.running);
  const projectId = useWorkspace((s) => s.projectId);
  const mcu = useWorkspace((s) => s.mcu);
  const runBuild = useWorkspace((s) => s.runBuild);
  const runFlash = useWorkspace((s) => s.runFlash);
  const stopAgent = useWorkspace((s) => s.stopAgent);
  const startDemo = useWorkspace((s) => s.startDemo);
  const project = projects.find((p) => p.id === projectId) ?? projects[0];

  return (
    <header className="flex h-10 shrink-0 items-center gap-3 border-b border-border bg-chrome px-3">
      <Link href="/" className="flex items-center gap-2 pr-2">
        <span className="flex size-5 items-center justify-center rounded-sm bg-primary text-[10px] font-bold text-primary-foreground">
          C
        </span>
        <span className="hidden text-[12px] font-semibold tracking-tight lg:inline">
          C-Embedded Agent
        </span>
      </Link>

      <div className="hidden items-center gap-2 text-[11px] text-muted-foreground md:flex">
        <span className="rounded-sm border border-border bg-panel px-1.5 py-0.5 text-foreground">
          {project.name}
        </span>
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
            agentStatus === "working" && "pulse-dot bg-info",
            agentStatus === "ready" && "bg-success",
            agentStatus === "error" && "bg-error",
            agentStatus === "stopped" && "bg-warning",
          )}
        />
        <span className="truncate font-medium">
          {agentStatus === "working" ? "Agent Working" : agentStatus === "ready" ? "Agent Ready" : statusText}
        </span>
        {agentStatus === "working" && (
          <span className="hidden truncate text-muted-foreground sm:inline">{statusText}</span>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1">
        <Button onClick={runBuild} title="Ctrl+B">
          <Hammer />
          Build
        </Button>
        <Button variant="success" onClick={() => { startDemo(); router.push("/agent"); }}>
          <Play />
          Run
        </Button>
        <Button variant="secondary" onClick={runFlash} title="Ctrl+Shift+F">
          <Upload />
          Flash
        </Button>
        <Button variant="outline" onClick={() => router.push("/debug")}>
          <Bug />
          Debug
        </Button>
        <Button variant="destructive" disabled={!running && agentStatus !== "working"} onClick={stopAgent}>
          <Square />
          Stop
        </Button>
        <Button variant="ghost" size="icon" asChild>
          <Link href="/settings">
            <Settings />
          </Link>
        </Button>
        <span className="ml-1 flex size-6 items-center justify-center rounded-sm bg-accent text-[10px] font-semibold">
          JH
        </span>
      </div>
    </header>
  );
}

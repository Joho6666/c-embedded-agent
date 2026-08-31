"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "@/components/project/ProjectCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { projects } from "@/lib/mock/projects";
import { historyTasks } from "@/lib/mock/build";
import { useWorkspace } from "@/lib/stores/workspace";

export default function DashboardPage() {
  const router = useRouter();
  const startDemo = useWorkspace((s) => s.startDemo);

  return (
    <div className="mx-auto max-w-6xl p-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-[11px] text-muted-foreground">C-Embedded Agent</div>
          <h1 className="mt-1 text-[22px] font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1 text-[12px] text-muted-foreground">专注 C 语言与嵌入式开发的 AI 工程师</p>
        </div>
        <Button
          onClick={() => {
            startDemo();
            router.push("/agent");
          }}
        >
          <Play />
          STM32 LED Demo
        </Button>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2 md:grid-cols-4">
        {[
          ["项目", "12"],
          ["最近 Build", "8"],
          ["成功率", "87%"],
          ["Agent Fix", "23"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-sm border border-border bg-panel p-3">
            <div className="text-[11px] text-muted-foreground">你有 · {k}</div>
            <div className="mt-1 font-mono text-[22px]">{v}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2 text-[12px] md:grid-cols-4">
        {[
          ["/agent", "Agent Workspace"],
          ["/code", "Code Editor"],
          ["/build", "Build"],
          ["/problems", "Problems"],
          ["/serial", "Serial"],
          ["/debug", "Debug"],
          ["/mcu/pins", "Pin Map"],
          ["/projects/new", "新建项目"],
        ].map(([href, label]) => (
          <Link key={href} href={href} className="rounded-sm border border-border bg-panel px-3 py-2 hover:bg-accent">
            {label}
          </Link>
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <h2 className="text-[13px] font-medium">最近项目</h2>
        <Link href="/projects" className="text-[12px] text-muted-foreground hover:text-foreground">
          全部项目
        </Link>
      </div>
      <div className="mt-2 grid gap-2 md:grid-cols-3">
        {projects.slice(1, 4).map((p) => (
          <ProjectCard key={p.id} project={p} />
        ))}
      </div>

      <h2 className="mt-6 text-[13px] font-medium">Recent Agent Tasks</h2>
      <div className="mt-2 divide-y divide-border rounded-sm border border-border bg-panel">
        {historyTasks.map((t) => (
          <Link key={t.id} href="/agent" className="flex items-center justify-between px-3 py-2 hover:bg-accent/40">
            <div>
              <div className="text-[13px]">{t.title}</div>
              <div className="text-[11px] text-muted-foreground">
                {t.projectName} · {t.createdAt}
              </div>
            </div>
            <StatusBadge status={t.status} label={t.status === "working" ? "● Working" : "✓ Complete"} />
          </Link>
        ))}
      </div>
    </div>
  );
}

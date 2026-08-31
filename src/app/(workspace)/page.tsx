"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "@/components/project/ProjectCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { projects } from "@/lib/mock/projects";
import { historyTasks } from "@/lib/mock/build";
import { useAgent } from "@/lib/stores/agent-store";

export default function DashboardPage() {
  const router = useRouter();
  const start = useAgent((s) => s.startGoldenPath);
  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-[11px] tracking-wide text-muted-foreground">C-Embedded Agent</div>
          <h1 className="mt-1 text-[24px] font-semibold tracking-tight">欢迎回来</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">专注 C 语言与嵌入式开发的 AI 工程师</p>
        </div>
        <Button
          onClick={() => {
            void start();
            router.push("/agent");
          }}
        >
          <Play />
          STM32 LED 演示
        </Button>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-2 md:grid-cols-4">
        {[
          ["项目", "12"],
          ["最近构建", "8"],
          ["成功率", "87%"],
          ["Agent 修复", "23"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-md border border-border bg-panel p-3.5 hover:border-zinc-600">
            <div className="text-[11px] text-muted-foreground">{k}</div>
            <div className="mt-1 font-mono text-[22px] tracking-tight">{v}</div>
          </div>
        ))}
      </div>
      <div className="mt-5 grid grid-cols-2 gap-2 text-[12px] md:grid-cols-4">
        {[
          ["/agent", "Agent 工作区"],
          ["/code", "代码编辑器"],
          ["/build", "构建"],
          ["/problems", "问题"],
          ["/serial", "串口"],
          ["/debug", "调试"],
          ["/mcu/pins", "引脚图"],
          ["/projects/new", "新建项目"],
        ].map(([href, label]) => (
          <Link
            key={href}
            href={href}
            className="rounded-md border border-border bg-panel px-3 py-2.5 hover:border-zinc-600 hover:bg-accent/60"
          >
            {label}
          </Link>
        ))}
      </div>
      <h2 className="mt-7 text-[13px] font-medium">最近项目</h2>
      <div className="mt-2 grid gap-2 md:grid-cols-3">
        {projects.slice(1, 4).map((p) => (
          <ProjectCard key={p.id} project={p} />
        ))}
      </div>
      <h2 className="mt-7 text-[13px] font-medium">最近 Agent 任务</h2>
      <div className="mt-2 divide-y divide-border overflow-hidden rounded-md border border-border bg-panel">
        {historyTasks.map((t) => (
          <Link key={t.id} href="/agent" className="flex items-center justify-between px-3 py-2.5 hover:bg-accent/40">
            <div>
              <div className="text-[13px]">{t.title}</div>
              <div className="text-[11px] text-muted-foreground">
                {t.projectName} · {t.createdAt}
              </div>
            </div>
            <StatusBadge status={t.status} label={t.status === "working" ? "● 进行中" : "✓ 完成"} />
          </Link>
        ))}
      </div>
    </div>
  );
}

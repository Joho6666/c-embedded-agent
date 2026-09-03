"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/common/Empty";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useLive } from "@/lib/stores/live-store";
import { loadToday, loadProjects, createProject } from "@/lib/os/service";
import type { OsActivity, OsProject, OsTask, OsToday } from "@/types/os";
import { TASK_STATUS_LABEL } from "@/types/os";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning.";
  if (h < 18) return "Good afternoon.";
  return "Good evening.";
}

function TaskRow({ task }: { task: OsTask }) {
  return (
    <Link
      href={`/projects/${task.projectId}?tab=tasks&task=${task.id}`}
      className="flex items-center justify-between gap-2 border-t border-border px-3 py-2 text-[12px] hover:bg-accent/40"
    >
      <span className="truncate">{task.title}</span>
      <StatusBadge status={task.status} label={TASK_STATUS_LABEL[task.status]} />
    </Link>
  );
}

function ActivityLine({ item }: { item: OsActivity }) {
  return (
    <li className="border-t border-border px-3 py-1.5 text-[12px] text-muted-foreground">
      <span className="font-mono text-[11px] text-foreground/80">{item.createdAt.slice(11, 16) || "—"}</span>{" "}
      <span className="text-foreground">{item.actorType}</span> {item.verb} {item.objectType}
    </li>
  );
}

export default function TodayPage() {
  const mode = useLive((s) => s.mode);
  const [today, setToday] = useState<OsToday | null>(null);
  const [projects, setProjects] = useState<OsProject[]>([]);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");

  const reload = () => {
    void loadToday().then(setToday);
    void loadProjects().then(setProjects);
  };

  useEffect(() => {
    reload();
  }, [mode]);

  const hourLabel = useMemo(() => greeting(), []);

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto max-w-[1100px] space-y-4 p-5">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="text-[11px] text-muted-foreground">MyOS · Today</div>
            <h1 className="text-[22px] font-semibold tracking-tight">{hourLabel}</h1>
            <p className="mt-1 text-[13px] text-muted-foreground">今天人和 Agent 正在推进什么？</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href="/start">开始固件工程</Link>
            </Button>
            <form
              className="flex gap-1"
              onSubmit={(e) => {
                e.preventDefault();
                const n = name.trim() || "Untitled project";
                setCreating(true);
                void createProject({ name: n }).then(() => {
                  setName("");
                  setCreating(false);
                  reload();
                });
              }}
            >
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="New project"
                className="h-7 w-40 rounded-sm border border-border bg-background px-2 text-[12px] outline-none"
              />
              <Button type="submit" disabled={creating}>
                Create project
              </Button>
            </form>
          </div>
        </header>

        {mode !== "live" && (
          <div className="rounded-md border border-border bg-panel px-3 py-2 text-[12px] text-muted-foreground">
            DEMO / OFFLINE：OS 数据在本机保存。C-Agent 真执行需要 LIVE 后端与 firmware workspace。
          </div>
        )}

        <section className="grid gap-2 sm:grid-cols-3">
          {[
            { label: "Need Attention", value: today?.counts.attention ?? 0 },
            { label: "Agents Running", value: today?.counts.running ?? 0 },
            { label: "Blocked", value: today?.counts.blocked ?? 0 },
          ].map((c) => (
            <div key={c.label} className="rounded-md border border-border bg-panel px-3 py-2">
              <div className="text-[11px] text-muted-foreground">{c.label}</div>
              <div className="text-[20px] font-semibold tabular-nums">{c.value}</div>
            </div>
          ))}
        </section>

        {today?.focus && (
          <section className="rounded-md border border-border bg-panel p-3">
            <div className="text-[11px] text-muted-foreground">Today’s Focus</div>
            <Link href={`/projects/${today.focus.projectId}?tab=tasks&task=${today.focus.id}`} className="mt-1 block text-[14px] hover:text-primary">
              {today.focus.title}
            </Link>
            <StatusBadge status={today.focus.status} label={TASK_STATUS_LABEL[today.focus.status]} />
          </section>
        )}

        <div className="grid gap-3 lg:grid-cols-2">
          <section className="rounded-md border border-border bg-panel">
            <h2 className="px-3 py-2 text-[12px] font-medium">My Tasks</h2>
            {today?.myTasks.length ? today.myTasks.map((t) => <TaskRow key={t.id} task={t} />) : <div className="p-3"><Empty title="No open tasks" hint="Create a project task." /></div>}
          </section>
          <section className="rounded-md border border-border bg-panel">
            <h2 className="px-3 py-2 text-[12px] font-medium">Agent Running</h2>
            {today?.agentRunning.length ? today.agentRunning.map((t) => <TaskRow key={t.id} task={t} />) : <div className="px-3 py-6 text-[12px] text-muted-foreground">没有正在跑的 Agent。</div>}
          </section>
          <section className="rounded-md border border-border bg-panel">
            <h2 className="px-3 py-2 text-[12px] font-medium">Needs Review</h2>
            {today?.needsReview.length ? today.needsReview.map((t) => <TaskRow key={t.id} task={t} />) : <div className="px-3 py-6 text-[12px] text-muted-foreground">没有待审核结果。</div>}
          </section>
          <section className="rounded-md border border-border bg-panel">
            <h2 className="px-3 py-2 text-[12px] font-medium">Blocked</h2>
            {today?.blocked.length ? today.blocked.map((t) => <TaskRow key={t.id} task={t} />) : <div className="px-3 py-6 text-[12px] text-muted-foreground">没有卡住的任务。</div>}
          </section>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-md border border-border bg-panel">
            <h2 className="px-3 py-2 text-[12px] font-medium">Recent Activity</h2>
            <ul>
              {(today?.recentActivity ?? []).slice(0, 12).map((a) => (
                <ActivityLine key={a.id} item={a} />
              ))}
            </ul>
          </section>
          <section className="rounded-md border border-border bg-panel">
            <div className="flex items-center justify-between px-3 py-2">
              <h2 className="text-[12px] font-medium">Recent Projects</h2>
              <Link href="/projects" className="text-[11px] text-primary">全部</Link>
            </div>
            {projects.length === 0 ? (
              <div className="px-3 py-6 text-[12px] text-muted-foreground">还没有项目。</div>
            ) : (
              projects.slice(0, 8).map((p) => (
                <Link key={p.id} href={`/projects/${p.id}`} className="flex items-center justify-between border-t border-border px-3 py-2 text-[12px] hover:bg-accent/40">
                  <span>{p.name}</span>
                  <span className="tabular-nums text-muted-foreground">{p.progress}%</span>
                </Link>
              ))
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "@/components/project/ProjectCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ReliabilityPanel } from "@/components/dashboard/ReliabilityPanel";
import { ProjectHealth } from "@/components/dashboard/ProjectHealth";
import { useAgent } from "@/lib/stores/agent-store";
import { listProjects } from "@/lib/api/project";
import type { Project } from "@/types/project";
import { useLive } from "@/lib/stores/live-store";
import { getBenchmarkDashboard } from "@/lib/api/benchmark";
import { listErrorMemories } from "@/lib/api/memory";
import type { BenchmarkSummary } from "@/types/benchmark";
import type { ErrorMemoryEntry } from "@/types/memory";
import { API_BASE } from "@/lib/api/client";

export default function DashboardPage() {
  const router = useRouter();
  const start = useAgent((s) => s.startGoldenPath);
  const mode = useLive((s) => s.mode);
  const gcc = useLive((s) => s.gcc);
  const [bench, setBench] = useState<BenchmarkSummary | null>(null);
  const [memories, setMemories] = useState<ErrorMemoryEntry[]>([]);
  const [tools, setTools] = useState<string>("Not Tested");
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [recentRuns, setRecentRuns] = useState<Array<{ id: string; prompt?: string; status?: string; started_at?: string }>>([]);

  useEffect(() => {
    if (mode !== "live") return;
    void getBenchmarkDashboard().then(setBench);
    void listErrorMemories().then((r) => setMemories(r.available ? r.items.slice(0, 4) : []));
    void listProjects().then((rows) => setRecentProjects(rows.slice(0, 3)));
    void fetch(`${API_BASE}/api/runs`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d: Array<{ id: string; prompt?: string; status?: string; started_at?: string }>) => setRecentRuns(Array.isArray(d) ? d.slice(0, 8) : []))
      .catch(() => setRecentRuns([]));
    void fetch(`${API_BASE}/api/tools/status`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Array<{ id: string; installed?: boolean }>) => {
        const n = rows.filter((x) => x.installed).length;
        setTools(rows.length ? `${n}/${rows.length} tools` : "Not Tested");
      })
      .catch(() => setTools("Backend capability unavailable"));
  }, [mode]);

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-[11px] tracking-wide text-muted-foreground">C-Embedded Agent</div>
          <h1 className="mt-1 text-[24px] font-semibold tracking-tight">Engineering Dashboard</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">AI Embedded Firmware Engineer · STM32F103</p>
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
        <ReliabilityPanel data={mode === "live" ? bench : null} />
        <div className="rounded-md border border-border bg-panel p-3.5">
          <div className="text-[11px] text-muted-foreground">Toolchain</div>
          <div className="mt-1 font-mono text-[18px]">{mode === "live" ? tools : "DEMO"}</div>
          <div className="mt-1 text-[11px] text-muted-foreground">gcc {gcc ?? "unknown"}</div>
        </div>
        <div className="rounded-md border border-border bg-panel p-3.5">
          <div className="text-[11px] text-muted-foreground">Hardware</div>
          <div className="mt-1 font-mono text-[18px]">{mode === "live" ? "Probe LIVE" : "Not Tested"}</div>
        </div>
        <div className="rounded-md border border-border bg-panel p-3.5">
          <div className="text-[11px] text-muted-foreground">Knowledge</div>
          <div className="mt-1 font-mono text-[18px]">{mode === "live" ? "FTS5" : "DEMO"}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-2 md:grid-cols-3">
        <ProjectHealth build="Not Tested" warnings={0} hardware={mode === "live" ? "Unknown" : "Disconnected"} knowledge={mode === "live" ? "Indexed" : "Local"} agent="Ready" />
        <div className="rounded-md border border-border bg-panel p-3.5 md:col-span-2">
          <div className="text-[11px] text-muted-foreground">Shortcuts</div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-[12px] md:grid-cols-4">
            {[
              ["/agent", "Agent 工作区"],
              ["/ioc", "IOC Analysis"],
              ["/validation", "Hardware Validation"],
              ["/skills", "Embedded Skills"],
              ["/memory/errors", "Error Memory"],
              ["/benchmark", "Benchmark"],
              ["/serial", "串口"],
              ["/projects/new", "导入 CubeMX"],
            ].map(([href, label]) => (
              <Link key={href} href={href} className="rounded-md border border-border bg-panel-2 px-3 py-2.5 hover:border-zinc-600 hover:bg-accent/60">
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>

      <h2 className="mt-7 text-[13px] font-medium">Recent Projects</h2>
      <div className="mt-2 grid gap-2 md:grid-cols-3">
        {recentProjects.length === 0 ? (
          <div className="text-[12px] text-muted-foreground">无项目</div>
        ) : (
          recentProjects.map((p) => <ProjectCard key={p.id} project={p} />)
        )}
      </div>
      <h2 className="mt-7 text-[13px] font-medium">Recent Agent Runs</h2>
      <div className="mt-2 divide-y divide-border overflow-hidden rounded-md border border-border bg-panel">
        {recentRuns.length === 0 ? (
          <div className="px-3 py-2.5 text-[12px] text-muted-foreground">无记录</div>
        ) : (
          recentRuns.map((t) => (
            <Link key={t.id} href="/agent" className="flex items-center justify-between px-3 py-2.5 hover:bg-accent/40">
              <div>
                <div className="text-[13px]">{t.prompt || t.id}</div>
                <div className="text-[11px] text-muted-foreground">{t.started_at || ""}</div>
              </div>
              <StatusBadge status={t.status || "idle"} />
            </Link>
          ))
        )}
      </div>
      <h2 className="mt-7 text-[13px] font-medium">Weakest Skills / Error Memories / Benchmark Trend</h2>
      <div className="mt-2 grid gap-2 md:grid-cols-3">
        <div className="rounded-md border border-border bg-panel p-3 text-[12px] text-muted-foreground">
          Weakest Skills: {bench?.bySkill.length ? bench.bySkill.map((s) => s.name).join(", ") : "Not Tested"}
        </div>
        <div className="rounded-md border border-border bg-panel p-3 text-[12px]">
          {memories.length === 0 ? (
            <span className="text-muted-foreground">Recent Error Memories: 尚无已验证修复</span>
          ) : (
            memories.map((m) => (
              <Link key={m.id} href={`/memory/errors/${m.id}`} className="block truncate font-mono text-[11px] hover:underline">
                {m.pattern}
              </Link>
            ))
          )}
        </div>
        <div className="rounded-md border border-border bg-panel p-3 text-[12px] text-muted-foreground">
          Benchmark Trend: {bench?.compileSuccess == null ? "No benchmark data" : `${Math.round(bench.compileSuccess * 100)}% compile`}
        </div>
      </div>
    </div>
  );
}

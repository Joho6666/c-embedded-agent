"use client";

import { useEffect, useState } from "react";
import { testSuite } from "@/lib/mock/build";
import { StatusBadge } from "@/components/common/StatusBadge";
import { API_BASE } from "@/lib/api/client";
import { useLive } from "@/lib/stores/live-store";

interface Metrics {
  gcc?: boolean;
  llm?: boolean;
  skipped?: string[];
  first_build_success_rate?: number;
  compile_success_rate?: number;
  avg_iterations?: number;
  template_build?: boolean;
}

export default function TestingPage() {
  const mode = useLive((s) => s.mode);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    if (mode !== "live") return;
    void fetch(`${API_BASE}/api/metrics`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: Metrics | null) => setMetrics(d))
      .catch(() => setMetrics(null));
  }, [mode]);

  const pct = (v?: number) => (v == null ? "—" : `${Math.round(v * 100)}%`);

  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">测试 / Benchmark</h1>
      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="rounded-sm border border-border bg-panel p-3">
          <div className="text-[11px] text-muted-foreground">First Build Success</div>
          <div className="font-mono text-[20px]">{pct(metrics?.first_build_success_rate)}</div>
        </div>
        <div className="rounded-sm border border-border bg-panel p-3">
          <div className="text-[11px] text-muted-foreground">Compile Success</div>
          <div className="font-mono text-[20px]">{pct(metrics?.compile_success_rate)}</div>
        </div>
        <div className="rounded-sm border border-border bg-panel p-3">
          <div className="text-[11px] text-muted-foreground">Avg Iterations</div>
          <div className="font-mono text-[20px]">{metrics?.avg_iterations ?? "—"}</div>
        </div>
        <div className="rounded-sm border border-border bg-panel p-3">
          <div className="text-[11px] text-muted-foreground">Template make</div>
          <div className="font-mono text-[20px]">{metrics?.template_build == null ? "—" : metrics.template_build ? "ok" : "fail"}</div>
        </div>
      </div>
      {metrics?.skipped?.length ? (
        <p className="mt-3 text-[12px] text-muted-foreground">跳过：{metrics.skipped.join(" · ")}（不会伪装成功）</p>
      ) : null}
      <h2 className="mt-6 text-[13px] text-muted-foreground">DEMO 用例</h2>
      <div className="mt-2 rounded-sm border border-border">
        {testSuite.cases.map((c) => (
          <div key={c.name} className="flex items-center justify-between border-b border-border px-3 py-2 last:border-0">
            <span className="font-mono text-[12px]">{c.name}</span>
            <StatusBadge status={c.status === "pass" ? "success" : c.status === "fail" ? "failed" : "pending"} label={c.status} />
          </div>
        ))}
      </div>
    </div>
  );
}

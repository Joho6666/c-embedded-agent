"use client";

import { useEffect, useState } from "react";
import { BenchmarkDashboardView } from "@/components/benchmark/BenchmarkDashboard";
import { ModelComparison } from "@/components/benchmark/ModelComparison";
import { getBenchmarkDashboard } from "@/lib/api/benchmark";
import type { BenchmarkSummary } from "@/types/benchmark";
import { useLive } from "@/lib/stores/live-store";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";

export default function BenchmarkPage() {
  const mode = useLive((s) => s.mode);
  const [data, setData] = useState<BenchmarkSummary | null>(null);

  useEffect(() => {
    if (mode !== "live") {
      setData({
        available: false,
        reason: "Backend capability unavailable",
        bySkill: [],
        models: [],
      });
      return;
    }
    void getBenchmarkDashboard().then(setData);
  }, [mode]);

  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">STM32F103 Agent Benchmark</h1>
      <p className="text-[12px] text-muted-foreground">数据来自 results.json /api/metrics。没有真实跑分时显示 No benchmark data。</p>
      <div className="mt-4">
        {!data ? <CapabilityBanner reason="Loading…" /> : <BenchmarkDashboardView data={data} />}
      </div>
      <div className="mt-8">
        <ModelComparison rows={data?.models ?? []} />
      </div>
    </div>
  );
}

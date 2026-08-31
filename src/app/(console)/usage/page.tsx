"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Metric } from "@/components/common/Metric";
import { useGateway } from "@/lib/stores/gateway";
import { gatewayApi } from "@/lib/services/gateway";
import { formatCompact, formatMs, formatNumber, formatPercent, formatUsd } from "@/lib/format";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const ranges = ["today", "24h", "7d", "30d"] as const;

export default function UsagePage() {
  const m = useGateway((s) => s.metrics);
  const [range, setRange] = useState<(typeof ranges)[number]>("today");
  const [trend, setTrend] = useState<{ t: string; requests: number; tokens: number; cost: number }[]>([]);

  useEffect(() => {
    void gatewayApi
      .usageTrend(range)
      .then((d) => setTrend(d.trend || []))
      .catch(() => setTrend([]));
  }, [range]);

  return (
    <div>
      <PageHeader title="用量与成本" description="数据来自真实 RequestLog。未配置模型定价时成本为 0。" />
      <div className="mb-3 flex gap-1">
        {ranges.map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`rounded-md border px-2 py-1 text-[12px] ${range === r ? "border-foreground/40 bg-accent" : "border-border"}`}
          >
            {r}
          </button>
        ))}
      </div>
      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <Metric label="Requests" value={formatNumber(m.requestsToday)} />
        <Metric label="Tokens" value={formatCompact(m.tokensToday)} />
        <Metric label="Cost" value={formatUsd(m.estimatedCost)} />
        <Metric label="Success" value={formatPercent(m.successRate)} />
        <Metric label="Latency" value={formatMs(m.avgLatencyMs)} />
      </div>
      <div className="rounded-lg border border-border bg-card p-3">
        <div className="mb-2 text-[12px] font-medium">Request Trend</div>
        {trend.length === 0 ? (
          <div className="py-10 text-center text-[12px] text-muted-foreground">暂无请求数据</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={trend}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: 12 }} />
              <Area type="monotone" dataKey="requests" stroke="#e4e4e7" fill="#27272a" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

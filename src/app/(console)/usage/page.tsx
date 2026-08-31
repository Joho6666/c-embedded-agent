"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Metric } from "@/components/common/Metric";
import { useGateway } from "@/lib/stores/gateway";
import { gatewayApi } from "@/lib/services/gateway";
import { formatCompact, formatMs, formatNumber, formatPercent, formatUsd } from "@/lib/format";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const ranges = ["today", "24h", "7d", "30d"] as const;

type Slice = { id: string; name: string; requests?: number; tokens?: number; cost?: number; successRate?: number; latency?: number; ttft?: number; count429?: number; count5xx?: number; timeout?: number; fallbackRate?: number };

export default function UsagePage() {
  const m = useGateway((s) => s.metrics);
  const [range, setRange] = useState<(typeof ranges)[number]>("today");
  const [trend, setTrend] = useState<{ t: string; requests: number; tokens: number; cost: number }[]>([]);
  const [providers, setProviders] = useState<Slice[]>([]);
  const [models, setModels] = useState<Slice[]>([]);
  const [credentials, setCredentials] = useState<Slice[]>([]);
  const [keys, setKeys] = useState<Slice[]>([]);
  const [errors, setErrors] = useState<{ name: string; value: number }[]>([]);

  useEffect(() => {
    void gatewayApi.usageTrend(range).then((d) => setTrend(d.trend || [])).catch(() => setTrend([]));
    void gatewayApi.usageProviders(range).then((d) => setProviders(d as Slice[])).catch(() => setProviders([]));
    void gatewayApi.usageModels(range).then((d) => setModels(d as Slice[])).catch(() => setModels([]));
    void gatewayApi.usageCredentials(range).then((d) => setCredentials(d as Slice[])).catch(() => setCredentials([]));
    void gatewayApi.usageApiKeys(range).then((d) => setKeys(d as Slice[])).catch(() => setKeys([]));
    void gatewayApi.usageErrors(range).then((d) => setErrors(d)).catch(() => setErrors([]));
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
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <Breakdown title="Provider Cost" rows={providers} />
        <Breakdown title="Model Cost" rows={models} />
        <Breakdown title="Credential Cost" rows={credentials} />
        <Breakdown title="API Key Cost" rows={keys} />
      </div>
      <div className="mt-4 rounded-lg border border-border bg-card p-3">
        <div className="mb-2 text-[12px] font-medium">Errors · 429 / 5xx / Timeout</div>
        <div className="flex flex-wrap gap-2 text-[12px]">
          {errors.map((e) => (
            <div key={e.name} className="rounded-sm border border-border px-2 py-1">
              {e.name} <span className="font-mono">{e.value}</span>
            </div>
          ))}
          {errors.length === 0 && <span className="text-muted-foreground">暂无错误</span>}
        </div>
      </div>
    </div>
  );
}

function Breakdown({ title, rows }: { title: string; rows: Slice[] }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="mb-2 text-[12px] font-medium">{title}</div>
      {rows.length === 0 ? (
        <div className="text-[12px] text-muted-foreground">暂无数据</div>
      ) : (
        <table className="w-full text-left text-[12px]">
          <thead className="text-[11px] text-muted-foreground">
            <tr>
              <th className="py-1">Name</th>
              <th>Req</th>
              <th>Tokens</th>
              <th>Cost</th>
              <th>OK</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-border">
                <td className="py-1">{r.name}</td>
                <td className="font-mono">{r.requests ?? 0}</td>
                <td className="font-mono">{formatCompact(r.tokens ?? 0)}</td>
                <td className="font-mono">{formatUsd(r.cost ?? 0, 4)}</td>
                <td className="font-mono">{formatPercent(r.successRate ?? 100)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

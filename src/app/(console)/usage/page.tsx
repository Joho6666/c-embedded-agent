"use client";

import { useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Metric } from "@/components/common/Metric";
import { usageByRange } from "@/lib/mock";
import type { UsageRange } from "@/types";
import { formatCompact, formatMs, formatNumber, formatPercent, formatUsd } from "@/lib/format";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const ranges: UsageRange[] = ["today", "24h", "7d", "30d"];

export default function UsagePage() {
  const [range, setRange] = useState<UsageRange>("today");
  const d = usageByRange[range];

  return (
    <div>
      <PageHeader title="用量与成本" description="Spend tracking · Provider / Model / Credential / Client 分布。" />
      <div className="mb-3 flex gap-1">
        {ranges.map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`rounded-sm border px-2 py-1 text-[12px] ${range === r ? "border-foreground/40 bg-accent" : "border-border"}`}
          >
            {r}
          </button>
        ))}
      </div>
      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <Metric label="Requests" value={formatNumber(d.totals.requests)} />
        <Metric label="Tokens" value={formatCompact(d.totals.tokens)} />
        <Metric label="Cost" value={formatUsd(d.totals.cost)} />
        <Metric label="Success" value={formatPercent(d.totals.successRate)} />
        <Metric label="Latency" value={formatMs(d.totals.latency)} />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Request Trend">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={d.trend}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: 12 }} />
              <Area type="monotone" dataKey="requests" stroke="#e4e4e7" fill="#27272a" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Token / Cost Trend">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={d.trend}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: 12 }} />
              <Area type="monotone" dataKey="tokens" stroke="#3b82f6" fill="#1e3a5f" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Provider Share">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.byProvider}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: 12 }} />
              <Bar dataKey="value">
                {d.byProvider.map((p) => (
                  <Cell key={p.id} fill={p.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Error Distribution">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.errors}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: 12 }} />
              <Bar dataKey="value" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <List title="Virtual Model" rows={d.byModel} />
        <List title="API Key" rows={d.byKey} />
        <List title="Credential family" rows={d.byCredential} />
      </div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <div className="mb-2 text-[12px] font-medium">{title}</div>
      {children}
    </div>
  );
}

function List({ title, rows }: { title: string; rows: { name: string; value: number }[] }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <div className="mb-2 text-[12px] font-medium">{title}</div>
      {rows.map((r) => (
        <div key={r.name} className="flex justify-between py-0.5 text-[12px]">
          <span>{r.name}</span>
          <span className="font-mono text-muted-foreground">{r.value}%</span>
        </div>
      ))}
    </div>
  );
}

"use client";

import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { UsageChart } from "@/components/charts/UsageChart";
import { CostChart } from "@/components/charts/CostChart";
import { LatencyChart } from "@/components/charts/LatencyChart";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatCompact, formatLatency, formatPercent, formatTokens, formatUsd } from "@/lib/format";
import { tooltipStyle } from "@/components/charts/chart-theme";
import type { RankItem, TimeRange } from "@/types";

const pieColors = ["var(--foreground)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "#52525b"];

function Rank({ title, items, format }: { title: string; items: RankItem[]; format: (n: number) => string }) {
  return (
    <Card className="p-3">
      <div className="mb-2 text-[12px] font-medium">{title}</div>
      <div className="divide-y divide-border">
        {items.map((item, i) => (
          <div key={item.id} className="flex items-center justify-between py-1.5 text-[12px]">
            <div className="flex items-center gap-2">
              <span className="w-4 font-mono text-muted-foreground">{i + 1}</span>
              {item.name}
            </div>
            <span className="font-mono text-muted-foreground">{item.extra ?? format(item.value)}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function isoDate(offsetDays: number) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function AnalyticsPage() {
  const [range, setRange] = useState<TimeRange>("7d");
  const [from, setFrom] = useState(isoDate(-13));
  const [to, setTo] = useState(isoDate(0));
  const [applied, setApplied] = useState({ from: isoDate(-13), to: isoDate(0) });
  const { data, loading, error, reload } = useAsync(
    () => api.getAnalytics(range === "custom" ? { range, from: applied.from, to: applied.to } : range),
    [range, applied.from, applied.to],
  );
  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? undefined} onRetry={reload} />;

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader
        title={t.analytics.title}
        subtitle={t.analytics.subtitle}
        actions={
          <Tabs value={range} onValueChange={(v) => setRange(v as TimeRange)}>
            <TabsList>
              <TabsTrigger value="today">{t.common.today}</TabsTrigger>
              <TabsTrigger value="7d">{t.common.range7}</TabsTrigger>
              <TabsTrigger value="30d">{t.common.range30}</TabsTrigger>
              <TabsTrigger value="custom">{t.common.custom}</TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />
      {range === "custom" && (
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <Label>{t.analytics.from}</Label>
            <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>{t.analytics.to}</Label>
            <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <Button onClick={() => setApplied({ from, to })}>{t.common.apply}</Button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
        <MetricCard label={t.dashboard.requests} value={formatCompact(data.totals.requests)} />
        <MetricCard label={t.dashboard.tokens} value={formatTokens(data.totals.tokens)} />
        <MetricCard label={t.dashboard.cost} value={formatUsd(data.totals.cost)} />
        <MetricCard label={t.dashboard.latency} value={formatLatency(data.totals.latency)} />
        <MetricCard label={t.analytics.errorRate} value={formatPercent(data.totals.errorRate)} />
      </div>
      <div className="grid gap-2 lg:grid-cols-2">
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.analytics.requestTrend}</div>
          <UsageChart data={data.series} dataKey="requests" />
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.analytics.tokenTrend}</div>
          <UsageChart data={data.series} dataKey="tokens" />
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.analytics.costTrend}</div>
          <CostChart data={data.series} />
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.analytics.latency}</div>
          <LatencyChart data={data.series} />
        </Card>
      </div>
      <div className="grid gap-2 lg:grid-cols-2">
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.analytics.modelDist}</div>
          <div className="h-[220px]">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={data.modelDistribution} dataKey="value" nameKey="name" innerRadius={48} outerRadius={80} paddingAngle={2}>
                  {data.modelDistribution.map((_, i) => (
                    <Cell key={i} fill={pieColors[i % pieColors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.analytics.providerDist}</div>
          <div className="h-[220px]">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={data.providerDistribution} dataKey="value" nameKey="name" innerRadius={48} outerRadius={80} paddingAngle={2}>
                  {data.providerDistribution.map((_, i) => (
                    <Cell key={i} fill={pieColors[i % pieColors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        <Rank title={t.analytics.expensive} items={data.ranks.expensiveModels} format={(n) => `$${n}`} />
        <Rank title={t.analytics.popular} items={data.ranks.popularModels} format={formatCompact} />
        <Rank title={t.analytics.slowest} items={data.ranks.slowestProviders} format={formatLatency} />
        <Rank title={t.analytics.failing} items={data.ranks.failingProviders} format={(n) => formatPercent(n)} />
        <Rank title={t.analytics.topKeys} items={data.ranks.topKeys} format={formatUsd} />
      </div>
    </div>
  );
}

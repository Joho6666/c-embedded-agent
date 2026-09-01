"use client";

import { Card } from "@/components/ui/card";
import { MetricCard } from "@/components/common/MetricCard";
import { HealthBadge } from "@/components/common/HealthBadge";
import { PageHeader } from "@/components/common/PageHeader";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { UsageChart } from "@/components/charts/UsageChart";
import { CostChart } from "@/components/charts/CostChart";
import { LatencyChart } from "@/components/charts/LatencyChart";
import { Badge } from "@/components/ui/badge";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatCompact, formatDateTime, formatLatency, formatPercent, formatTokens, formatUsd, relativeTime } from "@/lib/format";

export function DashboardPage() {
  const { data, loading, error, reload } = useAsync(() => api.getDashboard(), []);
  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? undefined} onRetry={reload} />;

  return (
    <div className="mx-auto max-w-[1280px] space-y-5 p-5 md:p-6">
      <PageHeader title={t.dashboard.title} subtitle={t.dashboard.subtitle} />
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4 xl:grid-cols-7">
        <MetricCard label={t.dashboard.requests} value={formatCompact(data.todayRequests)} delta={data.deltas.requests} />
        <MetricCard label={t.dashboard.tokens} value={formatTokens(data.todayTokens)} delta={data.deltas.tokens} />
        <MetricCard label={t.dashboard.cost} value={formatUsd(data.todayCost)} delta={data.deltas.cost} />
        <MetricCard label={t.dashboard.success} value={formatPercent(data.successRate)} delta={data.deltas.successRate} />
        <MetricCard label={t.dashboard.latency} value={formatLatency(data.avgLatency)} delta={data.deltas.latency} />
        <MetricCard label={t.dashboard.activeKeys} value={String(data.activeKeys)} />
        <MetricCard label={t.dashboard.online} value={String(data.onlineProviders)} />
      </div>
      <div className="grid gap-2 lg:grid-cols-2">
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.requestTrend}</div>
          <UsageChart data={data.series} dataKey="requests" />
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.tokenTrend}</div>
          <UsageChart data={data.series} dataKey="tokens" />
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.costTrend}</div>
          <CostChart data={data.series} />
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.latencyTrend}</div>
          <LatencyChart data={data.series} />
        </Card>
      </div>
      <div className="grid gap-2 lg:grid-cols-2">
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.modelRank}</div>
          <div className="divide-y divide-border">
            {data.modelRank.map((m, i) => (
              <div key={m.id} className="flex items-center justify-between py-1.5 text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="w-4 font-mono text-muted-foreground">{i + 1}</span>
                  <span className="font-mono">{m.name}</span>
                </div>
                <span className="font-mono text-muted-foreground">{formatCompact(m.value)}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.providerHealth}</div>
          <div className="divide-y divide-border">
            {data.providerHealth.map((p) => (
              <div key={p.id} className="flex items-center justify-between py-1.5 text-[12px]">
                <div className="flex items-center gap-2">
                  <span>{p.name}</span>
                  <HealthBadge status={p.health} />
                </div>
                <span className="font-mono text-muted-foreground">
                  {formatPercent(p.successRate)} · {formatLatency(p.latency)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className="grid gap-2 lg:grid-cols-3">
        <Card className="p-3 lg:col-span-2">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.recent}</div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <tbody>
                {data.recentLogs.map((l) => (
                  <tr key={l.id} className="border-t border-border">
                    <td className="py-1.5 pr-3 font-mono text-[11px] text-muted-foreground">{formatDateTime(l.time)}</td>
                    <td className="py-1.5 pr-3 font-mono">{l.model}</td>
                    <td className="py-1.5 pr-3">{l.user}</td>
                    <td className="py-1.5 pr-3">
                      <Badge tone={l.status === "success" ? "success" : "error"}>{l.status}</Badge>
                    </td>
                    <td className="py-1.5 font-mono text-muted-foreground">{formatLatency(l.latency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-[12px] font-medium">{t.dashboard.alerts}</div>
          <div className="space-y-2">
            {data.alerts.map((a) => (
              <div key={a.id} className="rounded-sm border border-border p-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] font-medium">{a.title}</span>
                  <Badge tone={a.severity === "error" ? "error" : "warning"}>{a.severity}</Badge>
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">{a.detail}</p>
                <p className="mt-1 text-[10px] text-muted-foreground">{relativeTime(a.time)}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { HealthBadge } from "@/components/common/HealthBadge";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { Card } from "@/components/ui/card";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatLatency, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

export function MonitorPage() {
  const { data, loading, error, reload } = useAsync(() => api.getMonitor(), []);
  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? undefined} onRetry={reload} />;

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader title={t.monitor.title} subtitle={t.monitor.subtitle} />
      <div className="grid gap-2">
        {data.map((row) => (
          <Card key={row.providerId} className="p-3.5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-medium">{row.name}</span>
                  <HealthBadge status={row.health} />
                </div>
                <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">{row.endpoint}</div>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[11px] sm:grid-cols-5">
                <Stat k={t.monitor.success} v={formatPercent(row.successRate)} />
                <Stat k="P50" v={formatLatency(row.p50)} />
                <Stat k="P95" v={formatLatency(row.p95)} />
                <Stat k="P99" v={formatLatency(row.p99)} />
                <Stat k={t.monitor.errorRate} v={formatPercent(row.errorRate)} />
              </div>
            </div>
            <div className="mt-3">
              <div className="mb-1 text-[10px] text-muted-foreground">{t.monitor.uptime}</div>
              <div className="flex gap-[3px]">
                {row.uptime.map((v, i) => (
                  <span
                    key={i}
                    title={`${i}:00`}
                    className={cn(
                      "h-6 flex-1 rounded-[2px]",
                      v === 1 && "bg-success",
                      v === 0.5 && "bg-warning",
                      v === 0 && "bg-muted",
                    )}
                  />
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="text-muted-foreground">{k}</div>
      <div>{v}</div>
    </div>
  );
}

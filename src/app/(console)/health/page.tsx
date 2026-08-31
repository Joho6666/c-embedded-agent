"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { ProvStatus } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatMs, formatPercent } from "@/lib/format";
import { toast } from "sonner";

export default function HealthPage() {
  const health = useGateway((s) => s.health);
  const refresh = useGateway((s) => s.refreshHealth);
  const providers = useGateway((s) => s.providers);

  return (
    <div>
      <PageHeader
        title="健康状态"
        description="Gateway · Database · Redis · Providers · Credentials · Models · Worker"
        actions={
          <Button
            onClick={async () => {
              await refresh();
              toast.success("Health check 完成");
            }}
          >
            Health Check
          </Button>
        }
      />
      <div className="mb-4 text-[12px] text-muted-foreground">上次检查 {formatDateTime(health.checkedAt)}</div>
      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {health.components.map((c) => (
          <div key={c.id} className="rounded-md border border-border bg-card p-3">
            <div className="flex items-center justify-between">
              <div className="text-[13px]">{c.name}</div>
              <Badge tone={c.status === "operational" ? "success" : c.status === "degraded" ? "warning" : "error"}>
                {c.status}
              </Badge>
            </div>
            <div className="mt-1 text-[11px] text-muted-foreground">{c.detail}</div>
            {c.latencyMs != null && <div className="font-mono text-[11px]">{formatMs(c.latencyMs)}</div>}
          </div>
        ))}
      </div>
      <div className="mb-3 text-[12px] font-medium">Provider Health</div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {providers.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
            <div>
              <div className="text-[12px]">{p.name}</div>
              <div className="text-[11px] text-muted-foreground">
                {formatMs(p.latencyMs)} · {formatPercent(p.successRate, 1)}
              </div>
            </div>
            <ProvStatus status={p.status} />
          </div>
        ))}
      </div>
      <div className="mt-4 text-[12px] font-medium">Credential Health</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {health.credentialCounts.map((c) => (
          <div key={c.status} className="rounded-sm border border-border px-2 py-1 text-[12px]">
            {c.status} <span className="font-mono">{c.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

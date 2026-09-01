"use client";

import { HealthBadge } from "@/components/common/HealthBadge";
import { Card } from "@/components/ui/card";
import { formatLatency, formatPercent, formatPricePerM } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Provider, RoutePolicy } from "@/types";

export function RouteGraph({
  route,
  providers,
}: {
  route: RoutePolicy;
  providers: Provider[];
}) {
  const name = (id: string) => providers.find((p) => p.id === id)?.name ?? id;
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch">
      <Card className="flex min-w-[140px] flex-col justify-center p-3">
        <div className="text-[10px] text-muted-foreground">alias</div>
        <div className="font-mono text-[13px]">{route.modelAlias}</div>
        <div className="mt-1 text-[12px] text-muted-foreground">{route.displayName}</div>
      </Card>
      <div className="hidden items-center text-muted-foreground lg:flex">→</div>
      <Card className="flex min-w-[140px] flex-col justify-center p-3">
        <div className="text-[10px] text-muted-foreground">{t.routing.policy}</div>
        <div className="text-[13px] font-medium">{t.strategy[route.strategy]}</div>
      </Card>
      <div className="hidden items-center text-muted-foreground lg:flex">→</div>
      <div className="min-w-0 flex-1 space-y-2">
        {route.targets.map((target) => (
          <Card key={target.providerId} className="flex flex-wrap items-center justify-between gap-2 p-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium">{name(target.providerId)}</span>
                <HealthBadge status={target.health} />
              </div>
              <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                {t.providers.weight} {target.weight}% · P{target.priority}
              </div>
            </div>
            <div className="flex gap-4 font-mono text-[11px] text-muted-foreground">
              <span>{formatPercent(target.successRate)}</span>
              <span>{formatLatency(target.avgLatency)}</span>
              <span>{formatPricePerM(target.inputPrice)}</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-foreground" style={{ width: `${target.weight}%` }} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { RouteGraph } from "@/components/routing/RouteGraph";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { RoutePolicy, RouteStrategy, RouteTarget } from "@/types";

const strategies: RouteStrategy[] = ["cheapest", "fastest", "stable", "weighted", "random", "failover", "custom"];

function normalize(targets: RouteTarget[], id: string, weight: number) {
  return targets.map((t) => (t.providerId === id ? { ...t, weight } : t));
}

function moveTarget(targets: RouteTarget[], id: string, dir: -1 | 1) {
  const next = [...targets];
  const i = next.findIndex((t) => t.providerId === id);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= next.length) return next;
  [next[i], next[j]] = [next[j], next[i]];
  return next.map((t, idx) => ({ ...t, priority: idx + 1 }));
}

export function RoutingPage() {
  const routes = useAsync(() => api.listRoutes(), []);
  const providers = useAsync(() => api.listProviders(), []);
  const [busy, setBusy] = useState<string | null>(null);

  const patch = async (id: string, run: () => Promise<RoutePolicy>) => {
    setBusy(id);
    try {
      const next = await run();
      routes.setData((prev) => (prev ?? []).map((r) => (r.id === next.id ? next : r)));
      toast.success(t.routing.updated);
    } finally {
      setBusy(null);
    }
  };

  if (routes.loading || providers.loading) return <PageSkeleton />;
  if (routes.error || !routes.data) return <ErrorState message={routes.error ?? undefined} onRetry={routes.reload} />;

  return (
    <div className="mx-auto max-w-[1100px] space-y-4 p-5 md:p-6">
      <PageHeader title={t.routing.title} subtitle={t.routing.subtitle} />
      <div className="space-y-4">
        {(routes.data ?? []).map((route) => (
          <Card key={route.id} className="space-y-3 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-mono text-[13px]">{route.modelAlias}</div>
              <Select
                value={route.strategy}
                disabled={busy === route.id}
                onValueChange={(v) => patch(route.id, () => api.updateRoute(route.id, v as RouteStrategy))}
              >
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((s) => (
                    <SelectItem key={s} value={s}>
                      {t.strategy[s]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <RouteGraph
              route={route}
              providers={providers.data ?? []}
              onWeight={(providerId, weight) => {
                const targets = normalize(route.targets, providerId, weight);
                routes.setData((prev) => (prev ?? []).map((r) => (r.id === route.id ? { ...r, targets, strategy: "custom" } : r)));
                void api.updateRoute(route.id, { strategy: "custom", targets });
              }}
              onRemove={(providerId) => patch(route.id, () => api.removeRouteTarget(route.id, providerId))}
              onAdd={(providerId) => patch(route.id, () => api.addRouteTarget(route.id, providerId))}
              onMove={(providerId, dir) => {
                const targets = moveTarget(route.targets, providerId, dir);
                void patch(route.id, () => api.updateRoute(route.id, { strategy: "custom", targets }));
              }}
            />
          </Card>
        ))}
      </div>
    </div>
  );
}

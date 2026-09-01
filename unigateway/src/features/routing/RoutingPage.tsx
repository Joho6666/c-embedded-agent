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
import type { RouteStrategy } from "@/types";

const strategies: RouteStrategy[] = ["cheapest", "fastest", "stable", "weighted", "random", "failover", "custom"];

export function RoutingPage() {
  const routes = useAsync(() => api.listRoutes(), []);
  const providers = useAsync(() => api.listProviders(), []);
  const [busy, setBusy] = useState<string | null>(null);

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
                onValueChange={async (v) => {
                  setBusy(route.id);
                  try {
                    const next = await api.updateRoute(route.id, v as RouteStrategy);
                    routes.setData((prev) => (prev ?? []).map((r) => (r.id === next.id ? next : r)));
                    toast.success(t.routing.updated);
                  } finally {
                    setBusy(null);
                  }
                }}
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
            <RouteGraph route={route} providers={providers.data ?? []} />
          </Card>
        ))}
      </div>
    </div>
  );
}

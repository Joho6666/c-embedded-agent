"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import type { RoutingStrategy } from "@/types";
import { Switch } from "@/components/ui/switch";

const STRATEGIES: RoutingStrategy[] = [
  "priority",
  "round_robin",
  "weighted_round_robin",
  "least_latency",
  "least_load",
  "lowest_cost",
  "highest_success",
  "quota_aware",
  "health_aware",
  "failover",
  "random",
  "hybrid",
];

export default function RoutingPage() {
  const vms = useGateway((s) => s.virtualModels);
  const routes = useGateway((s) => s.routes);
  const models = useGateway((s) => s.models);
  const creds = useGateway((s) => s.credentials);
  const updateRoute = useGateway((s) => s.updateRoute);
  const [id, setId] = useState(vms[0]?.id);

  const vm = vms.find((v) => v.id === id) ?? vms[0];
  const route = routes.find((r) => r.virtualModelId === vm?.id);

  const ordered = useMemo(() => {
    return [...(route?.targets ?? [])].sort((a, b) => a.priority - b.priority);
  }, [route]);

  if (!vm || !route) return null;

  return (
    <div>
      <PageHeader title="路由策略" description="可视化候选权重、智能规则与 Fallback Chain。" />
      <div className="mb-3 flex flex-wrap gap-1">
        {vms.map((v) => (
          <button
            key={v.id}
            onClick={() => setId(v.id)}
            className={`rounded-sm border px-2 py-1 font-mono text-[12px] ${v.id === vm.id ? "border-foreground/40 bg-accent" : "border-border"}`}
          >
            {v.slug}
          </button>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-md border border-border bg-card p-3">
          <div className="mb-2 text-[12px] font-medium">Router · {vm.slug}</div>
          <div className="mb-3 flex flex-wrap gap-1">
            {STRATEGIES.map((s) => (
              <button
                key={s}
                onClick={() => updateRoute(vm.id, { strategy: s })}
                className={`rounded-sm border px-2 py-0.5 text-[11px] ${route.strategy === s ? "border-foreground/40 bg-accent" : "border-border"}`}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="space-y-2">
            {ordered.map((t, i) => {
              const m = models.find((x) => x.id === t.modelId);
              const c = creds.find((x) => x.id === t.credentialId);
              return (
                <div key={t.id} className="rounded-sm border border-border px-3 py-2">
                  <div className="flex items-center justify-between text-[12px]">
                    <span>
                      {i + 1}. {m?.modelId}
                      <span className="ml-2 text-[11px] text-muted-foreground">{c?.name}</span>
                    </span>
                    <span className="font-mono">{t.weight}%</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-sm bg-muted">
                    <div className="h-full bg-foreground/70" style={{ width: `${t.weight}%` }} />
                  </div>
                  <div className="mt-2 flex gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={i === 0}
                      onClick={() => {
                        const next = ordered.map((x, idx) =>
                          idx === i ? { ...x, priority: ordered[i - 1].priority } : idx === i - 1 ? { ...x, priority: t.priority } : x,
                        );
                        updateRoute(vm.id, { targets: next });
                      }}
                    >
                      上移
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const next = route.targets.map((x) =>
                          x.id === t.id ? { ...x, weight: Math.min(90, x.weight + 5) } : x,
                        );
                        updateRoute(vm.id, { targets: next });
                      }}
                    >
                      权重 +5
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="space-y-3">
          <div className="rounded-md border border-border bg-card p-3">
            <div className="mb-2 text-[12px] font-medium">智能规则</div>
            <div className="space-y-2">
              {route.rules.map((r) => (
                <div key={r.id} className="flex items-center justify-between gap-2 text-[12px]">
                  <span>
                    如果 <span className="font-mono">{r.when}</span> → {r.action}
                  </span>
                  <Switch
                    checked={r.enabled}
                    onCheckedChange={(v) =>
                      updateRoute(vm.id, {
                        rules: route.rules.map((x) => (x.id === r.id ? { ...x, enabled: v } : x)),
                      })
                    }
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-md border border-border bg-card p-3">
            <div className="mb-3 text-[12px] font-medium">Fallback Chain</div>
            <ol className="relative ml-3 border-l border-border">
              {vm.fallbackChain.map((hop, i) => (
                <li key={hop} className="mb-4 ml-4">
                  <span className="absolute -left-1 mt-1 size-2 rounded-full bg-foreground" />
                  <div className="font-mono text-[13px]">{hop}</div>
                  {i < vm.fallbackChain.length - 1 && (
                    <div className="text-[11px] text-muted-foreground">↓ fail · 429 / timeout / 5xx</div>
                  )}
                  {i === vm.fallbackChain.length - 1 && <div className="text-[11px] text-success">success / last hop</div>}
                </li>
              ))}
            </ol>
            <div className="rounded-sm border border-border bg-panel-2 px-2 py-2 font-mono text-[11px] text-muted-foreground">
              {vm.slug}
              {vm.fallbackChain.map((h) => (
                <div key={h}>↓ {h}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { useGateway } from "@/lib/stores/gateway";
import type { RoutingStrategy } from "@/types";

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
  const models = useGateway((s) => s.models);
  const creds = useGateway((s) => s.credentials);
  const updateRoute = useGateway((s) => s.updateRoute);
  const [id, setId] = useState(vms[0]?.id);

  const vm = vms.find((v) => v.id === id) ?? vms[0];

  const ordered = useMemo(() => {
    return [...(vm?.candidates ?? [])].sort((a, b) => a.priority - b.priority);
  }, [vm]);

  if (!vm) return <PageHeader title="路由策略" description="先创建一个 Virtual Model。" />;

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
                className={`rounded-sm border px-2 py-0.5 text-[11px] ${vm.strategy === s ? "border-foreground/40 bg-accent" : "border-border"}`}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="space-y-2">
            {ordered.map((t, i) => {
              const m = models.find((x) => x.id === t.modelId) ?? models.find((x) => x.modelId === t.modelId);
              const c = creds.find((x) => x.id === t.credentialId);
              return (
                <div key={`${t.modelId}-${i}`} className="rounded-sm border border-border px-3 py-2">
                  <div className="flex items-center justify-between text-[12px]">
                    <span>
                      {i + 1}. {m?.modelId ?? t.modelId}
                      <span className="ml-2 text-[11px] text-muted-foreground">{c?.name}</span>
                    </span>
                    <span className="font-mono">{t.weight}%</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-sm bg-muted">
                    <div className="h-full bg-foreground/70" style={{ width: `${t.weight}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="space-y-3">
          <div className="rounded-md border border-border bg-card p-3">
            <div className="mb-2 text-[12px] font-medium">智能规则（Gateway 已生效）</div>
            <div className="space-y-2 text-[12px] text-muted-foreground">
              <div>HTTP 429 / 5xx / timeout → 切换 Credential（最多 3 次）</div>
              <div>HTTP 401 / 403 → 标记 unauthorized，不重试该 Key</div>
              <div>连续失败 ≥ 5 → circuit_open，60s 后试探恢复</div>
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

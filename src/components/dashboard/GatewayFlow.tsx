"use client";

import { useEffect, useState } from "react";
import { useGateway } from "@/lib/stores/gateway";
import { formatNumber } from "@/lib/format";

export function GatewayFlow() {
  const healthy = useGateway((s) => s.credentials.filter((c) => c.status === "healthy").length);
  const metrics = useGateway((s) => s.metrics);
  const vms = useGateway((s) => s.virtualModels);
  const providers = useGateway((s) => s.providers);
  const [rpm, setRpm] = useState(0);

  useEffect(() => {
    setRpm(metrics.rpm);
  }, [metrics.rpm]);

  const stages = [
    { title: "Clients", sub: `${metrics.activeClients} Active` },
    { title: "API Gateway", sub: `${rpm} req/min` },
    { title: "Virtual Model", sub: `${vms.length} aliases` },
    { title: "Smart Router", sub: "failover · health aware" },
  ];
  const totalReq = Math.max(1, providers.reduce((n, p) => n + p.requestsToday, 0));
  const trafficShare = providers
    .map((p) => ({ providerId: p.id, name: p.name, pct: Math.round((p.requestsToday / totalReq) * 100), color: p.color }))
    .filter((p) => p.pct > 0)
    .slice(0, 6);

  return (
    <div className="rounded-md border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-[12px] font-medium">Gateway Flow</div>
        <div className="text-[11px] text-muted-foreground">实时流量分配</div>
      </div>
      <div className="grid gap-2 lg:grid-cols-[1fr_16px_1fr_16px_1fr_16px_1fr]">
        {stages.map((s, i) => (
          <div key={s.title} className="contents">
            <div className="rounded-sm border border-border bg-panel-2 px-3 py-2">
              <div className="text-[11px] text-muted-foreground">{s.title}</div>
              <div className="font-mono text-[13px]">{s.sub}</div>
            </div>
            {i < stages.length - 1 && <div className="flow-line hidden h-px self-center bg-border lg:block" />}
          </div>
        ))}
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-[1.4fr_0.6fr]">
        <div>
          <div className="mb-2 text-[11px] text-muted-foreground">Provider share</div>
          <div className="flex h-2 overflow-hidden rounded-sm">
            {trafficShare.map((t) => (
              <div key={t.providerId} style={{ width: `${t.pct}%`, background: t.color }} title={`${t.name} ${t.pct}%`} />
            ))}
          </div>
          <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
            {trafficShare.map((t) => (
              <div key={t.providerId} className="flex items-center justify-between text-[11px]">
                <span className="flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full" style={{ background: t.color }} />
                  {t.name}
                </span>
                <span className="font-mono text-muted-foreground">{t.pct}%</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-sm border border-border bg-panel-2 px-3 py-2">
          <div className="text-[11px] text-muted-foreground">Healthy Credentials</div>
          <div className="mt-1 font-mono text-[22px]">{formatNumber(healthy)}</div>
          <div className="text-[11px] text-muted-foreground">pool live · weight aware</div>
        </div>
      </div>
    </div>
  );
}

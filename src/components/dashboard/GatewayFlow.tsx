"use client";

import { useGateway } from "@/lib/stores/gateway";
import { formatNumber } from "@/lib/format";

export function GatewayFlow() {
  const credentials = useGateway((s) => s.credentials);
  const healthy = credentials.filter((c) => c.status === "healthy").length;
  const metrics = useGateway((s) => s.metrics);
  const vms = useGateway((s) => s.virtualModels);
  const providers = useGateway((s) => s.providers);
  const totalReq = providers.reduce((n, p) => n + p.requestsToday, 0);
  const trafficShare = providers
    .map((p) => ({
      providerId: p.id,
      name: p.name,
      pct: totalReq ? Math.round((p.requestsToday / totalReq) * 100) : 0,
      color: p.color,
    }))
    .filter((p) => p.pct > 0)
    .slice(0, 6);

  const stages = [
    { title: "Clients", sub: `${metrics.activeClients} active` },
    { title: "Gateway", sub: `${formatNumber(metrics.requestsToday)} today` },
    { title: "Virtual Model", sub: `${vms.length} aliases` },
    { title: "Router", sub: "failover · health" },
  ];

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[13px] font-medium">Gateway Flow</div>
        <div className="text-[11px] text-muted-foreground">live share from real usage</div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {stages.map((s, i) => (
          <div key={s.title} className="relative rounded-md border border-border bg-panel-2 px-3 py-2.5">
            {i < stages.length - 1 && (
              <span className="flow-line absolute top-1/2 -right-2 hidden h-px w-2 bg-border xl:block" />
            )}
            <div className="text-[11px] text-muted-foreground">{s.title}</div>
            <div className="mt-0.5 font-mono text-[13px]">{s.sub}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-[1.4fr_0.6fr]">
        <div>
          <div className="mb-2 text-[11px] text-muted-foreground">Provider share</div>
          {trafficShare.length === 0 ? (
            <div className="rounded-md border border-dashed border-border px-3 py-6 text-center text-[12px] text-muted-foreground">
              还没有请求。添加凭据后，流量会显示在这里。
            </div>
          ) : (
            <>
              <div className="flex h-2 overflow-hidden rounded-full">
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
            </>
          )}
        </div>
        <div className="rounded-md border border-border bg-panel-2 px-3 py-2.5">
          <div className="text-[11px] text-muted-foreground">Healthy Credentials</div>
          <div className="mt-1 font-mono text-[24px] tracking-tight">{formatNumber(healthy)}</div>
          <div className="text-[11px] text-muted-foreground">pool live · weight aware</div>
        </div>
      </div>
    </div>
  );
}

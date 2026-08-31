"use client";

import { useEffect, useState } from "react";
import { useGateway } from "@/lib/stores/gateway";
import { trafficShare } from "@/lib/mock";
import { overviewMetrics } from "@/lib/mock";
import { formatNumber } from "@/lib/format";

export function GatewayFlow() {
  const healthy = useGateway((s) => s.credentials.filter((c) => c.status === "healthy").length);
  const [rpm, setRpm] = useState(overviewMetrics.rpm);

  useEffect(() => {
    const t = setInterval(() => {
      setRpm((n) => Math.max(80, n + Math.round(Math.random() * 10 - 4)));
    }, 1800);
    return () => clearInterval(t);
  }, []);

  const stages = [
    { title: "Clients", sub: `${overviewMetrics.activeClients} Active` },
    { title: "API Gateway", sub: `${rpm} req/min` },
    { title: "Virtual Model", sub: "8 aliases" },
    { title: "Smart Router", sub: "hybrid + failover" },
  ];

  return (
    <div className="rounded-md border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-[12px] font-medium">Gateway Flow</div>
        <div className="text-[11px] text-muted-foreground">实时流量分配 · mock stream</div>
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

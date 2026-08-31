"use client";

import Link from "next/link";
import { Plus, TerminalSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Metric } from "@/components/common/Metric";
import { GatewayFlow } from "@/components/dashboard/GatewayFlow";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { formatCompact, formatMs, formatNumber, formatPercent, formatUsd } from "@/lib/format";
import { ProvStatus } from "@/components/common/StatusBadge";
import { ProviderMark } from "@/components/common/ProviderMark";

export default function OverviewPage() {
  const providers = useGateway((s) => s.providers);
  const openProv = useUi((s) => s.openAddProvider);
  const openCred = useUi((s) => s.openAddCredential);
  const m = useGateway((s) => s.metrics);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[18px] font-medium tracking-tight">Universal AI Gateway</h1>
          <p className="text-[12px] text-muted-foreground">One API. Every Model.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => openProv()}>
            <Plus className="size-3.5" /> 添加 Provider
          </Button>
          <Button variant="outline" onClick={() => openCred()}>
            <Plus className="size-3.5" /> 添加凭据
          </Button>
          <Button asChild>
            <Link href="/playground">
              <TerminalSquare className="size-3.5" /> API Playground
            </Link>
          </Button>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <Metric label="今日请求" value={formatNumber(m.requestsToday)} />
        <Metric label="Token" value={formatCompact(m.tokensToday)} />
        <Metric label="成功率" value={formatPercent(m.successRate)} />
        <Metric label="平均 TTFT" value={formatMs(m.avgTtftMs)} />
        <Metric label="估算成本" value={formatUsd(m.estimatedCost)} />
        <Metric label="平均延迟" value={formatMs(m.avgLatencyMs)} />
        <Metric label="总 Provider" value={m.activeProviders} />
        <Metric label="可用模型" value={m.availableModels} />
        <Metric label="活跃凭据" value={m.healthyCredentials} />
        <Metric label="熔断凭据" value={m.circuitOpen} hint="Circuit Open" />
      </div>

      <GatewayFlow />

      <div className="mt-4">
        <div className="mb-2 text-[12px] font-medium">Providers</div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {providers.slice(0, 6).map((p) => (
            <Link
              key={p.id}
              href={`/providers/${p.id}`}
              className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2 hover:bg-accent/40"
            >
              <div className="flex items-center gap-2">
                <ProviderMark mark={p.mark} color={p.color} />
                <div>
                  <div className="text-[12px]">{p.name}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {formatCompact(p.requestsToday)} req · {formatMs(p.latencyMs)}
                  </div>
                </div>
              </div>
              <ProvStatus status={p.status} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

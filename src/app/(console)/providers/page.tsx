"use client";

import Link from "next/link";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { ProviderMark } from "@/components/common/ProviderMark";
import { ProvStatus } from "@/components/common/StatusBadge";
import { CapabilityPills } from "@/components/common/CapabilityPills";
import { formatCompact, formatMs, formatPercent, formatUsd } from "@/lib/format";
import { gatewayApi } from "@/lib/services/gateway";
import { toast } from "sonner";

export default function ProvidersPage() {
  const providers = useGateway((s) => s.providers);
  const openProv = useUi((s) => s.openAddProvider);
  const openCred = useUi((s) => s.openAddCredential);

  return (
    <div>
      <PageHeader
        title="Provider"
        description="服务商级别接入。每个 Provider 可挂多个 Credential。"
        actions={<Button onClick={() => openProv()}>添加 Provider</Button>}
      />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {providers.map((p) => (
          <div key={p.id} className="rounded-md border border-border bg-card p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <ProviderMark mark={p.mark} color={p.color} />
                <div>
                  <div className="text-[13px] font-medium">{p.name}</div>
                  <div className="text-[11px] text-muted-foreground">{p.family}</div>
                </div>
              </div>
              <ProvStatus status={p.status} />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
              <Stat k="凭据" v={String(p.credentialCount)} />
              <Stat k="模型" v={String(p.modelCount)} />
              <Stat k="请求" v={formatCompact(p.requestsToday)} />
              <Stat k="Token" v={formatCompact(p.tokensToday)} />
              <Stat k="延迟" v={formatMs(p.latencyMs)} />
              <Stat k="成功率" v={formatPercent(p.successRate, 1)} />
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground">成本 {formatUsd(p.costToday)}</div>
            {p.local && (
              <div className="mt-1 text-[11px] text-muted-foreground">
                {p.host ?? p.baseUrl} {p.gpu ? `· ${p.gpu}` : ""}
              </div>
            )}
            <div className="mt-2">
              <CapabilityPills items={p.capabilities} max={6} />
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <Button size="sm" variant="outline" asChild>
                <Link href={`/providers/${p.id}`}>查看</Link>
              </Button>
              <Button size="sm" variant="outline" onClick={() => openCred(p.id)}>
                添加凭据
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  const r = await gatewayApi.syncModels(p.id);
                  toast.success(`已同步 ${r.synced} 个模型`);
                }}
              >
                同步模型
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  const r = await gatewayApi.testProvider(p.id);
                  toast[r.ok ? "success" : "error"](`${r.message} · ${r.latencyMs}ms`);
                }}
              >
                测试
              </Button>
              <Button size="sm" variant="ghost" asChild>
                <Link href={`/providers/${p.id}`}>配置</Link>
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="text-muted-foreground">{k}</div>
      <div className="font-mono">{v}</div>
    </div>
  );
}

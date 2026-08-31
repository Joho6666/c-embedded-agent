"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { formatCompact, formatPercent } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

export default function VirtualModelsPage() {
  const vms = useGateway((s) => s.virtualModels);
  const models = useGateway((s) => s.models);
  const creds = useGateway((s) => s.credentials);
  const open = useUi((s) => s.setCreateVirtualOpen);
  const update = useGateway((s) => s.updateVirtualModel);

  return (
    <div>
      <PageHeader
        title="虚拟模型"
        description="客户端只调用 model=&quot;coding&quot;。Gateway 解析候选并 Failover。"
        actions={<Button onClick={() => open(true)}>创建虚拟模型</Button>}
      />
      <div className="grid gap-3 lg:grid-cols-2">
        {vms.map((vm) => (
          <div key={vm.id} className="rounded-md border border-border bg-card p-3">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-mono text-[14px]">{vm.slug}</div>
                <div className="text-[12px] text-muted-foreground">{vm.description}</div>
              </div>
              <Badge>{vm.strategy}</Badge>
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground">
              {formatCompact(vm.requestsToday)} req · {formatPercent(vm.successRate, 1)}
            </div>
            <ol className="mt-3 space-y-1">
              {vm.candidates
                .slice()
                .sort((a, b) => a.priority - b.priority)
                .map((c, i) => {
                  const m = models.find((x) => x.id === c.modelId);
                  const cr = creds.find((x) => x.id === c.credentialId);
                  return (
                    <li key={i} className="flex items-center justify-between rounded-sm border border-border px-2 py-1 text-[12px]">
                      <span>
                        <span className="mr-2 font-mono text-muted-foreground">{c.priority}</span>
                        {m?.modelId}
                        <span className="ml-2 text-[11px] text-muted-foreground">{cr?.name}</span>
                      </span>
                      <span className="font-mono text-[11px]">{c.weight}%</span>
                    </li>
                  );
                })}
            </ol>
            <div className="mt-2 text-[11px] text-muted-foreground">Fallback: {vm.fallbackChain.join(" → ")}</div>
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={() => {
                const next = [...vm.candidates];
                if (next.length >= 2) {
                  const tmp = next[0].priority;
                  next[0] = { ...next[0], priority: next[1].priority };
                  next[1] = { ...next[1], priority: tmp };
                  update(vm.id, { candidates: next });
                }
              }}
            >
              交换前两优先级
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

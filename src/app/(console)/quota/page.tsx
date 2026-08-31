"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { useGateway } from "@/lib/stores/gateway";
import { formatCompact, formatUsd, quotaPct } from "@/lib/format";
import { CredStatus } from "@/components/common/StatusBadge";

export default function QuotaPage() {
  const creds = useGateway((s) => s.credentials);
  const providers = useGateway((s) => s.providers);
  const update = useGateway((s) => s.updateCredential);

  return (
    <div>
      <PageHeader title="额度 / Budget" description="RPM · TPM · Daily Token · Monthly Budget。80 / 90 / 95 / 100 告警。" />
      <div className="space-y-2">
        {creds.map((c) => {
          const p = providers.find((x) => x.id === c.providerId);
          const pct = quotaPct(c.quota.monthlySpend, c.quota.monthlyBudget || 1);
          const tokenPct = quotaPct(c.quota.dailyTokenUsed, c.quota.dailyTokenLimit);
          return (
            <div key={c.id} className="rounded-md border border-border bg-card p-3">
              <div className="mb-2 flex items-center justify-between">
                <div>
                  <div className="text-[13px]">{c.name}</div>
                  <div className="text-[11px] text-muted-foreground">{p?.name}</div>
                </div>
                <CredStatus status={c.status} />
              </div>
              <Row label="Monthly" used={`${formatUsd(c.quota.monthlySpend)} / ${formatUsd(c.quota.monthlyBudget)}`} pct={pct} />
              <Row label="Daily Token" used={`${formatCompact(c.quota.dailyTokenUsed)} / ${formatCompact(c.quota.dailyTokenLimit)}`} pct={tokenPct} />
              <Row label="RPM" used={`${c.quota.rpmUsed} / ${c.quota.rpmLimit}`} pct={quotaPct(c.quota.rpmUsed, c.quota.rpmLimit)} />
              <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                <label className="flex items-center gap-1">
                  RPM
                  <Input
                    className="h-6 w-20"
                    type="number"
                    value={c.quota.rpmLimit}
                    onChange={(e) => update(c.id, { quota: { ...c.quota, rpmLimit: Number(e.target.value) } })}
                  />
                </label>
                <label className="flex items-center gap-1">
                  Monthly $
                  <Input
                    className="h-6 w-20"
                    type="number"
                    value={c.quota.monthlyBudget}
                    onChange={(e) => update(c.id, { quota: { ...c.quota, monthlyBudget: Number(e.target.value) } })}
                  />
                </label>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Row({ label, used, pct }: { label: string; used: string; pct: number }) {
  return (
    <div className="mb-2">
      <div className="mb-0.5 flex justify-between text-[11px]">
        <span>{label}</span>
        <span className="font-mono text-muted-foreground">
          {used} · {pct.toFixed(0)}%
        </span>
      </div>
      <Progress value={pct} />
    </div>
  );
}

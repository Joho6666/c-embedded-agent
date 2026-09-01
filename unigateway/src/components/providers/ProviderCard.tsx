import { Card } from "@/components/ui/card";
import { HealthBadge } from "@/components/common/HealthBadge";
import { ProviderMark } from "@/components/common/ProviderMark";
import { formatCompact, formatLatency, formatPercent, formatUsd } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Provider } from "@/types";

export function ProviderCard({ provider }: { provider: Provider }) {
  return (
    <Card className="p-3.5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <ProviderMark type={provider.type} />
          <div>
            <div className="text-[13px] font-medium">{provider.name}</div>
            <div className="font-mono text-[11px] text-muted-foreground">{provider.baseUrl.replace("https://", "")}</div>
          </div>
        </div>
        <HealthBadge status={provider.health} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
        <div>
          <div className="text-muted-foreground">{t.providers.balance}</div>
          <div className="font-mono">{formatUsd(provider.balance)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">{t.providers.calls}</div>
          <div className="font-mono">{formatCompact(provider.todayCalls)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">{t.providers.success}</div>
          <div className="font-mono">{formatPercent(provider.successRate)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">{t.providers.latency}</div>
          <div className="font-mono">{formatLatency(provider.avgLatency)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">{t.providers.models}</div>
          <div className="font-mono">{provider.modelCount}</div>
        </div>
        <div>
          <div className="text-muted-foreground">{t.providers.weight}</div>
          <div className="font-mono">{provider.weight}</div>
        </div>
      </div>
    </Card>
  );
}

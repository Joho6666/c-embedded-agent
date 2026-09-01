"use client";

import { ChevronDown, ChevronUp, Plus, X } from "lucide-react";
import { HealthBadge } from "@/components/common/HealthBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { formatLatency, formatPercent, formatPricePerM } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Provider, RoutePolicy } from "@/types";

export function RouteGraph({
  route,
  providers,
  onWeight,
  onRemove,
  onAdd,
  onMove,
}: {
  route: RoutePolicy;
  providers: Provider[];
  onWeight: (providerId: string, weight: number) => void;
  onRemove: (providerId: string) => void;
  onAdd: (providerId: string) => void;
  onMove: (providerId: string, dir: -1 | 1) => void;
}) {
  const name = (id: string) => providers.find((p) => p.id === id)?.name ?? id;
  const available = providers.filter((p) => p.enabled && !route.targets.some((t) => t.providerId === p.id));
  const total = route.targets.reduce((s, t) => s + t.weight, 0) || 1;

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch">
      <Card className="flex min-w-[140px] flex-col justify-center p-3">
        <div className="text-[10px] text-muted-foreground">alias</div>
        <div className="font-mono text-[13px]">{route.modelAlias}</div>
        <div className="mt-1 text-[12px] text-muted-foreground">{route.displayName}</div>
      </Card>
      <div className="hidden items-center text-muted-foreground lg:flex">→</div>
      <Card className="flex min-w-[140px] flex-col justify-center p-3">
        <div className="text-[10px] text-muted-foreground">{t.routing.policy}</div>
        <div className="text-[13px] font-medium">{t.strategy[route.strategy]}</div>
        <div className="mt-2 text-[10px] text-muted-foreground">{t.routing.weightHint}</div>
      </Card>
      <div className="hidden items-center text-muted-foreground lg:flex">→</div>
      <div className="min-w-0 flex-1 space-y-2">
        {route.targets.map((target, i) => (
          <Card key={target.providerId} className="space-y-2 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium">{name(target.providerId)}</span>
                <HealthBadge status={target.health} />
              </div>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" disabled={i === 0} onClick={() => onMove(target.providerId, -1)} title={t.routing.moveUp}>
                  <ChevronUp />
                </Button>
                <Button variant="ghost" size="icon" disabled={i === route.targets.length - 1} onClick={() => onMove(target.providerId, 1)} title={t.routing.moveDown}>
                  <ChevronDown />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={route.targets.length <= 1}
                  onClick={() => onRemove(target.providerId)}
                  title={t.routing.removeTarget}
                >
                  <X />
                </Button>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="range"
                min={0}
                max={100}
                value={target.weight}
                onChange={(e) => onWeight(target.providerId, Number(e.target.value))}
                className="h-1.5 min-w-[160px] flex-1 accent-foreground"
              />
              <span className="w-10 font-mono text-[12px]">{Math.round((target.weight / total) * 100)}%</span>
              <span className="font-mono text-[11px] text-muted-foreground">P{target.priority}</span>
              <span className="font-mono text-[11px] text-muted-foreground">{formatPercent(target.successRate)}</span>
              <span className="font-mono text-[11px] text-muted-foreground">{formatLatency(target.avgLatency)}</span>
              <span className="font-mono text-[11px] text-muted-foreground">{formatPricePerM(target.inputPrice)}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-foreground" style={{ width: `${(target.weight / total) * 100}%` }} />
            </div>
          </Card>
        ))}
        {available.length > 0 ? (
          <Select onValueChange={onAdd}>
            <SelectTrigger className="w-full">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Plus className="size-3.5" />
                {t.routing.addTarget}
              </span>
            </SelectTrigger>
            <SelectContent>
              {available.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <div className="text-[11px] text-muted-foreground">{t.routing.noMore}</div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MoreHorizontal, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { HealthBadge } from "@/components/common/HealthBadge";
import { ProviderMark } from "@/components/common/ProviderMark";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { ProviderDrawer } from "@/components/providers/ProviderDrawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatCompact, formatLatency, formatPercent, formatUsd } from "@/lib/format";
import type { HealthStatus, Provider, ProviderInput } from "@/types";

export function ProvidersPage() {
  const { data, loading, error, reload, setData } = useAsync(() => api.listProviders(), []);
  const [q, setQ] = useState("");
  const [health, setHealth] = useState<HealthStatus | "all">("all");
  const [sort, setSort] = useState<"calls" | "latency" | "success">("calls");
  const [drawer, setDrawer] = useState(false);
  const [editing, setEditing] = useState<Provider | null>(null);
  const params = useSearchParams();
  useEffect(() => {
    if (params.get("new") === "1") {
      setEditing(null);
      setDrawer(true);
    }
  }, [params]);

  const rows = useMemo(() => {
    let list = data ?? [];
    if (q) list = list.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()) || p.baseUrl.includes(q));
    if (health !== "all") list = list.filter((p) => p.health === health);
    return [...list].sort((a, b) => {
      if (sort === "latency") return a.avgLatency - b.avgLatency;
      if (sort === "success") return b.successRate - a.successRate;
      return b.todayCalls - a.todayCalls;
    });
  }, [data, q, health, sort]);

  async function createOrEdit(input: ProviderInput) {
    if (editing) {
      const next = await api.updateProvider(editing.id, input);
      setData((prev) => (prev ?? []).map((p) => (p.id === next.id ? next : p)));
      toast.success(t.providers.updated);
      setEditing(null);
      return;
    }
    const created = await api.createProvider(input);
    setData((prev) => [created, ...(prev ?? [])]);
    toast.success(t.providers.created);
  }

  const columns: Column<Provider>[] = [
    {
      key: "name",
      header: t.common.name,
      render: (p) => (
        <div className="flex items-center gap-2">
          <ProviderMark type={p.type} />
          <div>
            <div className="font-medium">{p.name}</div>
            <div className="text-[11px] text-muted-foreground">{t.templates[p.type]}</div>
          </div>
        </div>
      ),
    },
    { key: "url", header: t.providers.baseUrl, render: (p) => <span className="font-mono text-[11px]">{p.baseUrl.replace("https://", "")}</span> },
    { key: "balance", header: t.providers.balance, render: (p) => <span className="font-mono">{formatUsd(p.balance)}</span> },
    { key: "models", header: t.providers.models, render: (p) => <span className="font-mono">{p.modelCount}</span> },
    { key: "calls", header: t.providers.calls, render: (p) => <span className="font-mono">{formatCompact(p.todayCalls)}</span> },
    { key: "ok", header: t.providers.success, render: (p) => <span className="font-mono">{formatPercent(p.successRate)}</span> },
    { key: "lat", header: t.providers.latency, render: (p) => <span className="font-mono">{formatLatency(p.avgLatency)}</span> },
    { key: "pri", header: t.providers.priority, render: (p) => p.priority },
    { key: "w", header: t.providers.weight, render: (p) => p.weight },
    { key: "h", header: t.providers.health, render: (p) => <HealthBadge status={p.health} /> },
    {
      key: "a",
      header: t.common.actions,
      render: (p) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem
              onSelect={async () => {
                const r = await api.testProvider(p.id);
                toast[r.ok ? "success" : "error"](`${r.message} · ${formatLatency(r.latency)}`);
              }}
            >
              {t.common.test}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                const r = await api.pullModels(p.id);
                setData((prev) => (prev ?? []).map((x) => (x.id === p.id ? { ...x, modelCount: r.count } : x)));
                toast.success(`${t.providers.pulled} · ${r.count}`);
              }}
            >
              {t.common.pullModels}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                const r = await api.queryBalance(p.id);
                setData((prev) => (prev ?? []).map((x) => (x.id === p.id ? { ...x, balance: r.balance } : x)));
                toast.success(`${t.providers.balanceUpdated} · ${formatUsd(r.balance)}`);
              }}
            >
              {t.common.queryBalance}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                const next = await api.toggleProvider(p.id);
                setData((prev) => (prev ?? []).map((x) => (x.id === next.id ? next : x)));
                toast.success(t.providers.toggled);
              }}
            >
              {p.enabled ? t.common.disable : t.common.enable}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => {
                setEditing(p);
                setDrawer(true);
              }}
            >
              {t.common.edit}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={async () => {
                if (!confirm(t.providers.confirmDelete)) return;
                await api.deleteProvider(p.id);
                setData((prev) => (prev ?? []).filter((x) => x.id !== p.id));
                toast.success(t.providers.deleted);
              }}
            >
              {t.common.delete}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  if (loading) return <PageSkeleton />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader
        title={t.providers.title}
        subtitle={t.providers.subtitle}
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setDrawer(true);
            }}
          >
            <Plus />
            {t.providers.add}
          </Button>
        }
      />
      <div className="flex flex-wrap gap-2">
        <Input className="max-w-56" placeholder={t.common.search} value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={health} onValueChange={(v) => setHealth(v as HealthStatus | "all")}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.common.all}</SelectItem>
            <SelectItem value="healthy">{t.health.healthy}</SelectItem>
            <SelectItem value="degraded">{t.health.degraded}</SelectItem>
            <SelectItem value="error">{t.health.error}</SelectItem>
            <SelectItem value="disabled">{t.health.disabled}</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={(v) => setSort(v as typeof sort)}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="calls">{t.providers.calls}</SelectItem>
            <SelectItem value="latency">{t.providers.latency}</SelectItem>
            <SelectItem value="success">{t.providers.success}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {rows.length === 0 ? <EmptyState /> : <DataTable columns={columns} rows={rows} />}
      <ProviderDrawer
        open={drawer}
        onOpenChange={setDrawer}
        initial={editing}
        onSubmit={createOrEdit}
      />
    </div>
  );
}

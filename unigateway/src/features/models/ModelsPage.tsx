"use client";

import { useMemo, useState } from "react";
import { MoreHorizontal, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { ModelBadge } from "@/components/common/ModelBadge";
import { PriceBadge } from "@/components/common/PriceBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { ModelDrawer } from "@/components/models/ModelDrawer";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatCompact, formatContext } from "@/lib/format";
import type { Model, ModelCapability, ModelInput } from "@/types";

const caps: ModelCapability[] = ["text", "vision", "reasoning", "image", "audio", "embedding", "tools"];

export function ModelsPage() {
  const models = useAsync(() => api.listModels(), []);
  const providers = useAsync(() => api.listProviders(), []);
  const [view, setView] = useState("table");
  const [q, setQ] = useState("");
  const [cap, setCap] = useState<ModelCapability | "all">("all");
  const [providerId, setProviderId] = useState("all");
  const [drawer, setDrawer] = useState(false);
  const [editing, setEditing] = useState<Model | null>(null);

  const nameOf = (id: string) => providers.data?.find((p) => p.id === id)?.name ?? id;

  const rows = useMemo(() => {
    let list = models.data ?? [];
    if (q) list = list.filter((m) => m.name.toLowerCase().includes(q.toLowerCase()) || m.alias.includes(q.toLowerCase()));
    if (cap !== "all") list = list.filter((m) => m.capabilities.includes(cap));
    if (providerId !== "all") list = list.filter((m) => m.providerId === providerId);
    return list;
  }, [models.data, q, cap, providerId]);

  async function save(input: ModelInput) {
    if (editing) {
      const next = await api.updateModel(editing.id, input);
      models.setData((prev) => (prev ?? []).map((m) => (m.id === next.id ? next : m)));
      toast.success(t.models.updated);
      setEditing(null);
      return;
    }
    const created = await api.createModel(input);
    models.setData((prev) => [created, ...(prev ?? [])]);
    toast.success(t.models.created);
  }

  const columns: Column<Model>[] = [
    { key: "name", header: t.common.name, render: (m) => <div><div>{m.name}</div><div className="font-mono text-[11px] text-muted-foreground">{m.alias}</div></div> },
    { key: "p", header: t.models.provider, render: (m) => nameOf(m.providerId) },
    { key: "in", header: t.models.input, render: (m) => <PriceBadge input={m.inputPrice} output={m.outputPrice} /> },
    { key: "ctx", header: t.models.context, render: (m) => <span className="font-mono">{formatContext(m.context)}</span> },
    { key: "cap", header: t.models.caps, render: (m) => <div className="flex flex-wrap gap-1">{m.capabilities.map((c) => <ModelBadge key={c} cap={c} />)}</div> },
    { key: "st", header: t.common.status, render: (m) => <Badge tone={m.status === "active" ? "success" : "neutral"}>{m.status}</Badge> },
    { key: "pref", header: t.models.preferred, render: (m) => nameOf(m.preferredProviderId) },
    { key: "c", header: t.models.calls, render: (m) => <span className="font-mono">{formatCompact(m.todayCalls)}</span> },
    {
      key: "a",
      header: t.common.actions,
      render: (m) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon"><MoreHorizontal /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onSelect={() => { setEditing(m); setDrawer(true); }}>{t.common.edit}</DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                const next = await api.updateModel(m.id, { status: m.status === "active" ? "disabled" : "active" });
                models.setData((prev) => (prev ?? []).map((x) => (x.id === next.id ? next : x)));
                toast.success(t.models.toggled);
              }}
            >
              {m.status === "active" ? t.common.disable : t.common.enable}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                if (!confirm(t.models.confirmDelete)) return;
                await api.deleteModel(m.id);
                models.setData((prev) => (prev ?? []).filter((x) => x.id !== m.id));
                toast.success(t.common.delete);
              }}
            >
              {t.common.delete}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  if (models.loading || providers.loading) return <PageSkeleton />;
  if (models.error) return <ErrorState message={models.error} onRetry={models.reload} />;

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader
        title={t.models.title}
        subtitle={t.models.subtitle}
        actions={
          <div className="flex items-center gap-2">
            <Tabs value={view} onValueChange={setView}>
              <TabsList>
                <TabsTrigger value="table">{t.models.table}</TabsTrigger>
                <TabsTrigger value="cards">{t.models.cards}</TabsTrigger>
              </TabsList>
            </Tabs>
            <Button onClick={() => { setEditing(null); setDrawer(true); }}>
              <Plus />
              {t.models.add}
            </Button>
          </div>
        }
      />
      <div className="flex flex-wrap gap-2">
        <Input className="max-w-56" placeholder={t.common.search} value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={cap} onValueChange={(v) => setCap(v as ModelCapability | "all")}>
          <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.common.all}</SelectItem>
            {caps.map((c) => (
              <SelectItem key={c} value={c}>{t.cap[c]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={providerId} onValueChange={setProviderId}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.common.all}</SelectItem>
            {(providers.data ?? []).map((p) => (
              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {rows.length === 0 ? (
        <EmptyState />
      ) : view === "cards" ? (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((m) => (
            <Card key={m.id} className="cursor-pointer p-3.5" onClick={() => { setEditing(m); setDrawer(true); }}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-[13px] font-medium">{m.name}</div>
                  <div className="font-mono text-[11px] text-muted-foreground">{m.alias}</div>
                </div>
                <Badge tone={m.status === "active" ? "success" : "neutral"}>{m.status}</Badge>
              </div>
              <div className="mt-2 text-[12px] text-muted-foreground">{nameOf(m.providerId)} · {formatContext(m.context)}</div>
              <div className="mt-2"><PriceBadge input={m.inputPrice} output={m.outputPrice} /></div>
              <div className="mt-2 flex flex-wrap gap-1">{m.capabilities.map((c) => <ModelBadge key={c} cap={c} />)}</div>
            </Card>
          ))}
        </div>
      ) : (
        <DataTable columns={columns} rows={rows} />
      )}
      <ModelDrawer
        open={drawer}
        onOpenChange={setDrawer}
        initial={editing}
        providers={providers.data ?? []}
        onSubmit={save}
      />
    </div>
  );
}

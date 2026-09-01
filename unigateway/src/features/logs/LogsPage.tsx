"use client";

import { useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { LogDetailDrawer } from "@/components/logs/LogDetailDrawer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatDateTime, formatLatency, formatNumber, formatUsd } from "@/lib/format";
import type { LogStatus, RequestLog } from "@/types";

export function LogsPage() {
  const [q, setQ] = useState("");
  const [model, setModel] = useState("all");
  const [providerId, setProviderId] = useState("all");
  const [status, setStatus] = useState<LogStatus | "all">("all");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<RequestLog | null>(null);

  const providers = useAsync(() => api.listProviders(), []);
  const logs = useAsync(() => api.listLogs({ q, model, providerId, status, page, pageSize: 12 }), [q, model, providerId, status, page]);

  const nameOf = (id: string) => providers.data?.find((p) => p.id === id)?.name ?? id;

  const columns: Column<RequestLog>[] = [
    { key: "t", header: t.logs.time, render: (l) => <span className="font-mono text-[11px]">{formatDateTime(l.time)}</span> },
    { key: "id", header: t.logs.requestId, render: (l) => <span className="font-mono text-[11px]">{l.requestId}</span> },
    { key: "u", header: t.logs.user, render: (l) => l.user },
    { key: "k", header: t.logs.key, render: (l) => l.keyName },
    { key: "m", header: t.logs.model, render: (l) => <span className="font-mono">{l.model}</span> },
    { key: "p", header: t.logs.provider, render: (l) => nameOf(l.providerId) },
    { key: "pt", header: t.logs.prompt, render: (l) => <span className="font-mono">{formatNumber(l.promptTokens)}</span> },
    { key: "ct", header: t.logs.completion, render: (l) => <span className="font-mono">{formatNumber(l.completionTokens)}</span> },
    { key: "c", header: t.logs.cost, render: (l) => <span className="font-mono">{formatUsd(l.cost, 4)}</span> },
    { key: "l", header: t.logs.latency, render: (l) => <span className="font-mono">{formatLatency(l.latency)}</span> },
    {
      key: "s",
      header: t.common.status,
      render: (l) => <Badge tone={l.status === "success" ? "success" : "error"}>{l.status}</Badge>,
    },
  ];

  if (logs.loading && !logs.data) return <PageSkeleton />;
  if (logs.error) return <ErrorState message={logs.error} onRetry={logs.reload} />;

  const totalPages = Math.max(1, Math.ceil((logs.data?.total ?? 0) / 12));

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader title={t.logs.title} subtitle={t.logs.subtitle} />
      <div className="flex flex-wrap gap-2">
        <Input className="max-w-56" placeholder={t.common.search} value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select value={model} onValueChange={(v) => { setModel(v); setPage(1); }}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.common.all}</SelectItem>
            {["gpt-4o", "claude-sonnet", "deepseek-chat", "gemini-pro", "o3"].map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={providerId} onValueChange={(v) => { setProviderId(v); setPage(1); }}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.common.all}</SelectItem>
            {(providers.data ?? []).map((p) => (
              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={(v) => { setStatus(v as LogStatus | "all"); setPage(1); }}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.common.all}</SelectItem>
            <SelectItem value="success">{t.logs.success}</SelectItem>
            <SelectItem value="error">{t.logs.fail}</SelectItem>
            <SelectItem value="timeout">timeout</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {!logs.data?.items.length ? (
        <EmptyState />
      ) : (
        <DataTable columns={columns} rows={logs.data.items} onRowClick={setSelected} />
      )}
      <div className="flex items-center justify-end gap-2 text-[12px] text-muted-foreground">
        <span>
          {t.common.total} {logs.data?.total ?? 0} {t.common.items}
        </span>
        <Button variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          {t.common.previous}
        </Button>
        <span>
          {page} {t.common.of} {totalPages}
        </span>
        <Button variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
          {t.common.next}
        </Button>
      </div>
      <LogDetailDrawer
        log={selected}
        providerName={selected ? nameOf(selected.providerId) : ""}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

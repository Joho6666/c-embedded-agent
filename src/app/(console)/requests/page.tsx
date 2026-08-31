"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { RequestStatus } from "@/components/common/StatusBadge";
import { formatClock, formatCompact, formatMs, formatUsd } from "@/lib/format";

const PAGE = 20;

export default function RequestsPage() {
  const logs = useGateway((s) => s.logs);
  const keys = useGateway((s) => s.keys);
  const providers = useGateway((s) => s.providers);
  const creds = useGateway((s) => s.credentials);
  const open = useUi((s) => s.openRequest);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [provider, setProvider] = useState("all");
  const [vm, setVm] = useState("all");
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    return logs.filter((l) => {
      const key = keys.find((k) => k.id === l.clientKeyId);
      const hit = `${l.callId} ${l.virtualModel} ${l.realModel} ${key?.name ?? ""}`.toLowerCase().includes(q.toLowerCase());
      const st = status === "all" || String(l.status) === status;
      const pr = provider === "all" || l.providerId === provider;
      const v = vm === "all" || l.virtualModel === vm;
      return hit && st && pr && v;
    });
  }, [logs, keys, q, status, provider, vm]);

  const slice = filtered.slice(page * PAGE, page * PAGE + PAGE);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));

  return (
    <div>
      <PageHeader title="请求日志" description="Datadog 风格的调用追踪。点击打开完整 Request Trace。" />
      <div className="mb-3 flex flex-wrap gap-2">
        <Input value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} placeholder="Request ID / model / client" className="max-w-64" />
        <select className="h-7 rounded-sm border border-input bg-panel-2 px-2 text-[12px]" value={status} onChange={(e) => { setStatus(e.target.value); setPage(0); }}>
          {["all", "200", "400", "401", "403", "429", "500", "502", "timeout", "quota_exhausted", "circuit_open"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select className="h-7 rounded-sm border border-input bg-panel-2 px-2 text-[12px]" value={provider} onChange={(e) => { setProvider(e.target.value); setPage(0); }}>
          <option value="all">all providers</option>
          {providers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <select className="h-7 rounded-sm border border-input bg-panel-2 px-2 text-[12px]" value={vm} onChange={(e) => { setVm(e.target.value); setPage(0); }}>
          <option value="all">all virtual</option>
          {[...new Set(logs.map((l) => l.virtualModel))].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </div>
      <div className="overflow-auto rounded-md border border-border">
        <table className="gw-table w-full min-w-[1200px] text-left text-[12px]">
          <thead className="bg-muted/40 text-[11px] text-muted-foreground">
            <tr>
              {["Time", "ID", "Client", "Virtual", "Real", "Provider", "Credential", "Status", "In", "Out", "TTFT", "Latency", "Retry", "FB", "Cost"].map(
                (h) => (
                  <th key={h} className="px-2 py-2 font-medium">
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {slice.map((l) => {
              const key = keys.find((k) => k.id === l.clientKeyId);
              const p = providers.find((x) => x.id === l.providerId);
              const c = creds.find((x) => x.id === l.credentialId);
              return (
                <tr key={l.id} className="cursor-pointer border-t border-border hover:bg-accent/40" onClick={() => open(l.id)}>
                  <td className="px-2 py-1.5 font-mono text-[11px]">{formatClock(l.time)}</td>
                  <td className="font-mono text-[11px]">{l.callId.slice(-10)}</td>
                  <td>{key?.name}</td>
                  <td className="font-mono">{l.virtualModel}</td>
                  <td className="font-mono text-[11px]">{l.realModel}</td>
                  <td>{p?.name}</td>
                  <td>{c?.name}</td>
                  <td>
                    <RequestStatus status={l.status} />
                  </td>
                  <td className="font-mono">{formatCompact(l.inputTokens)}</td>
                  <td className="font-mono">{formatCompact(l.outputTokens)}</td>
                  <td className="font-mono">{formatMs(l.ttftMs)}</td>
                  <td className="font-mono">{formatMs(l.latencyMs)}</td>
                  <td className="font-mono">{l.retries}</td>
                  <td className="font-mono">{l.fallbackCount}</td>
                  <td className="font-mono">{formatUsd(l.cost, 4)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between text-[12px]">
        <span className="text-muted-foreground">
          {filtered.length} requests · page {page + 1}/{pages}
        </span>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            Prev
          </Button>
          <Button size="sm" variant="outline" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

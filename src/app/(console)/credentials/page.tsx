"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { CredStatus } from "@/components/common/StatusBadge";
import { AUTH_SCHEME_LABEL } from "@/descriptors/providers";
import { formatCompact, formatMs, formatPercent, quotaPct, relativeTime, remainingLabel } from "@/lib/format";
import { Progress } from "@/components/ui/progress";
import type { CredentialStatus } from "@/types";

export default function CredentialsPage() {
  const creds = useGateway((s) => s.credentials);
  const providers = useGateway((s) => s.providers);
  const openAdd = useUi((s) => s.openAddCredential);
  const open = useUi((s) => s.openCredential);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string>("all");
  const [view, setView] = useState<"table" | "cards">("table");

  const filtered = useMemo(() => {
    return creds.filter((c) => {
      const p = providers.find((x) => x.id === c.providerId);
      const hit = `${c.name} ${p?.name ?? ""} ${c.authType}`.toLowerCase().includes(q.toLowerCase());
      return hit && (status === "all" || c.status === status);
    });
  }, [creds, providers, q, status]);

  const statuses: Array<"all" | CredentialStatus> = [
    "all",
    "healthy",
    "rate_limited",
    "cooling",
    "circuit_open",
    "unauthorized",
    "quota_exhausted",
    "disabled",
    "error",
  ];

  return (
    <div>
      <PageHeader
        title="凭据池 Credential Pool"
        description="多账号 / 多 Key / OAuth / Local。这是 Gateway 供给面的核心。"
        actions={<Button onClick={() => openAdd()}>添加凭据</Button>}
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索名称 / Provider" className="max-w-56" />
        <select
          className="h-7 rounded-sm border border-input bg-panel-2 px-2 text-[12px]"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <Button size="sm" variant={view === "table" ? "secondary" : "outline"} onClick={() => setView("table")}>
          表
        </Button>
        <Button size="sm" variant={view === "cards" ? "secondary" : "outline"} onClick={() => setView("cards")}>
          卡片
        </Button>
      </div>
      {view === "table" ? (
        <div className="overflow-auto rounded-md border border-border">
          <table className="gw-table w-full min-w-[1100px] text-left text-[12px]">
            <thead className="bg-muted/40 text-[11px] text-muted-foreground">
              <tr>
                {["名称", "Provider", "认证", "状态", "P", "权重", "请求", "Token", "RPM", "额度", "延迟", "成功率", "最后使用"].map(
                  (h) => (
                    <th key={h} className="px-2 py-2 font-medium">
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => {
                const p = providers.find((x) => x.id === c.providerId);
                const pct = quotaPct(c.quota.dailyTokenUsed, c.quota.dailyTokenLimit);
                return (
                  <tr
                    key={c.id}
                    className="cursor-pointer border-t border-border hover:bg-accent/40"
                    onClick={() => open(c.id)}
                  >
                    <td className="px-2 py-2">{c.name}</td>
                    <td>{p?.name}</td>
                    <td>{AUTH_SCHEME_LABEL[c.authType]}</td>
                    <td>
                      <div className="flex flex-col gap-0.5">
                        <CredStatus status={c.status} />
                        {c.status === "cooling" && (
                          <span className="font-mono text-[10px] text-sky-400">{remainingLabel(c.coolingUntil)} remaining</span>
                        )}
                      </div>
                    </td>
                    <td className="font-mono">{c.priority}</td>
                    <td className="font-mono">{c.weight}%</td>
                    <td className="font-mono">{formatCompact(c.requestsToday)}</td>
                    <td className="font-mono">{formatCompact(c.tokensToday)}</td>
                    <td className="font-mono">
                      {c.quota.rpmUsed}/{c.quota.rpmLimit}
                    </td>
                    <td className="w-28">
                      <Progress value={pct} />
                      <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">{pct.toFixed(0)}%</div>
                    </td>
                    <td className="font-mono">{formatMs(c.avgLatencyMs)}</td>
                    <td className="font-mono">{formatPercent(c.successRate, 1)}</td>
                    <td className="text-muted-foreground">{relativeTime(c.lastUsed)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((c) => {
            const p = providers.find((x) => x.id === c.providerId);
            return (
              <button
                key={c.id}
                onClick={() => open(c.id)}
                className="rounded-md border border-border bg-card p-3 text-left hover:bg-accent/30"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-[13px]">{c.name}</div>
                    <div className="text-[11px] text-muted-foreground">{p?.name}</div>
                  </div>
                  <CredStatus status={c.status} />
                </div>
                <div className="mt-2 grid grid-cols-3 gap-1 text-[11px] text-muted-foreground">
                  <span>P{c.priority}</span>
                  <span>{c.weight}%</span>
                  <span>{formatCompact(c.requestsToday)} req</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

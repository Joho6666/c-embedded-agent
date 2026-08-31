"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { ProviderMark } from "@/components/common/ProviderMark";
import { CapabilityPills } from "@/components/common/CapabilityPills";
import { CredStatus, ProvStatus } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatCompact, formatMs, formatPercent, formatUsd } from "@/lib/format";
import { Empty } from "@/components/common/Empty";

export default function ProviderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const provider = useGateway((s) => s.providers.find((p) => p.id === id));
  const creds = useGateway((s) => s.credentials.filter((c) => c.providerId === id));
  const models = useGateway((s) => s.models.filter((m) => m.providerId === id));
  const logs = useGateway((s) => s.logs.filter((l) => l.providerId === id).slice(0, 20));
  const openCred = useUi((s) => s.openAddCredential);
  const openC = useUi((s) => s.openCredential);
  const [tab, setTab] = useState("overview");

  if (!provider) return <Empty title="Provider 不存在" />;

  return (
    <div>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <ProviderMark mark={provider.mark} color={provider.color} size={36} />
          <div>
            <h1 className="text-[16px] font-medium">{provider.name}</h1>
            <div className="mt-0.5 flex items-center gap-2 text-[12px] text-muted-foreground">
              <ProvStatus status={provider.status} />
              {provider.baseUrl}
            </div>
          </div>
        </div>
        <Button onClick={() => openCred(provider.id)}>添加凭据</Button>
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="credentials">Credentials</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
          <TabsTrigger value="usage">Usage</TabsTrigger>
          <TabsTrigger value="errors">Errors</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-4 space-y-3">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <Box k="今日请求" v={formatCompact(provider.requestsToday)} />
            <Box k="Token" v={formatCompact(provider.tokensToday)} />
            <Box k="成本" v={formatUsd(provider.costToday)} />
            <Box k="成功率" v={formatPercent(provider.successRate)} />
          </div>
          <CapabilityPills items={provider.capabilities} />
          {provider.local && (
            <div className="rounded-md border border-border p-3 text-[12px]">
              Local · {provider.host ?? provider.baseUrl} · {provider.gpu ?? "CPU"} · Latency {formatMs(provider.latencyMs)}
            </div>
          )}
        </TabsContent>
        <TabsContent value="credentials" className="mt-4">
          <div className="space-y-1">
            {creds.map((c) => (
              <button
                key={c.id}
                className="flex w-full items-center justify-between rounded-sm border border-border px-3 py-2 text-left hover:bg-accent/40"
                onClick={() => openC(c.id)}
              >
                <span className="text-[12px]">{c.name}</span>
                <CredStatus status={c.status} />
              </button>
            ))}
          </div>
        </TabsContent>
        <TabsContent value="models" className="mt-4">
          <table className="w-full text-left text-[12px]">
            <thead className="text-[11px] text-muted-foreground">
              <tr>
                <th className="py-1">Model</th>
                <th>Context</th>
                <th>TTFT</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="border-t border-border">
                  <td className="py-1.5 font-mono">{m.modelId}</td>
                  <td>{m.contextWindow.toLocaleString()}</td>
                  <td>{formatMs(m.ttftMs)}</td>
                  <td>{m.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TabsContent>
        <TabsContent value="usage" className="mt-4 text-[12px]">
          今日 {formatCompact(provider.requestsToday)} 请求 · {formatCompact(provider.tokensToday)} tokens · {formatUsd(provider.costToday)}
          <div className="mt-2">
            <Link href="/usage" className="text-info hover:underline">
              打开用量页
            </Link>
          </div>
        </TabsContent>
        <TabsContent value="errors" className="mt-4">
          {logs.filter((l) => l.status !== 200).length === 0 ? (
            <Empty title="近期无错误" />
          ) : (
            logs
              .filter((l) => l.status !== 200)
              .map((l) => (
                <div key={l.id} className="flex justify-between border-b border-border py-1.5 font-mono text-[11px]">
                  <span>{l.callId.slice(-10)}</span>
                  <span>{String(l.status)}</span>
                </div>
              ))
          )}
        </TabsContent>
        <TabsContent value="settings" className="mt-4 text-[12px] text-muted-foreground">
          <div>Descriptor: {provider.descriptorId}</div>
          <div>Base URL: {provider.baseUrl ?? "—"}</div>
          <div>Auth: {provider.authSchemes.join(", ")}</div>
          <div>Endpoints: {provider.endpoints.join(", ")}</div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Box({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-md border border-border px-3 py-2">
      <div className="text-[11px] text-muted-foreground">{k}</div>
      <div className="font-mono text-[16px]">{v}</div>
    </div>
  );
}

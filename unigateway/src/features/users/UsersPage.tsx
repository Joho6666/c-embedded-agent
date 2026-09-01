"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatCompact, formatNumber, formatUsd } from "@/lib/format";
import type { Group, Plan, User } from "@/types";

export function UsersPage() {
  const { data, loading, error, reload } = useAsync(() => api.listUsers(), []);
  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? undefined} onRetry={reload} />;

  const planName = (id: string) => data.plans.find((p) => p.id === id)?.name ?? id;
  const groupName = (id: string) => data.groups.find((g) => g.id === id)?.name ?? id;

  const userCols: Column<User>[] = [
    { key: "n", header: t.common.name, render: (u) => <div><div>{u.name}</div><div className="text-[11px] text-muted-foreground">{u.email}</div></div> },
    { key: "r", header: t.common.type, render: (u) => <Badge>{t.role[u.role]}</Badge> },
    { key: "g", header: t.users.groups, render: (u) => groupName(u.groupId) },
    { key: "p", header: t.users.plans, render: (u) => planName(u.planId) },
    { key: "b", header: t.users.balance, render: (u) => <span className="font-mono">{formatUsd(u.balance)}</span> },
    { key: "s", header: t.users.spend, render: (u) => <span className="font-mono">{formatUsd(u.spend)}</span> },
    { key: "k", header: t.users.keys, render: (u) => u.keyCount },
    { key: "q", header: t.users.requests, render: (u) => <span className="font-mono">{formatNumber(u.requestCount)}</span> },
    { key: "st", header: t.common.status, render: (u) => <Badge tone={u.status === "active" ? "success" : "warning"}>{u.status}</Badge> },
  ];

  const groupCols: Column<Group>[] = [
    { key: "n", header: t.common.name, render: (g) => g.name },
    { key: "m", header: t.users.members, render: (g) => g.memberCount },
    { key: "p", header: t.users.plans, render: (g) => planName(g.planId) },
    { key: "s", header: t.users.spend, render: (g) => <span className="font-mono">{formatUsd(g.spend)}</span> },
  ];

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader title={t.users.title} subtitle={t.users.subtitle} />
      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">{t.users.users}</TabsTrigger>
          <TabsTrigger value="groups">{t.users.groups}</TabsTrigger>
          <TabsTrigger value="plans">{t.users.plans}</TabsTrigger>
        </TabsList>
        <TabsContent value="users" className="mt-3">
          <DataTable columns={userCols} rows={data.users} />
        </TabsContent>
        <TabsContent value="groups" className="mt-3">
          <DataTable columns={groupCols} rows={data.groups} />
        </TabsContent>
        <TabsContent value="plans" className="mt-3">
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {data.plans.map((p: Plan) => (
              <Card key={p.id} className="p-4">
                <div className="text-[13px] font-medium">{p.name}</div>
                <div className="mt-1 font-mono text-[22px]">{p.price === 0 ? t.role.free : formatUsd(p.price)}</div>
                <p className="mt-2 text-[12px] text-muted-foreground">{p.description}</p>
                <dl className="mt-3 space-y-1 font-mono text-[11px] text-muted-foreground">
                  <div>{t.users.quota} {formatCompact(p.monthlyQuota)}</div>
                  <div>RPM {p.rpm} · TPM {p.tpm.toLocaleString()}</div>
                </dl>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

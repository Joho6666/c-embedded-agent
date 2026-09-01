"use client";

import { useState } from "react";
import { MoreHorizontal, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { UserDrawer } from "@/components/users/UserDrawer";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatCompact, formatNumber, formatUsd } from "@/lib/format";
import type { Group, Plan, User, UserInput } from "@/types";

export function UsersPage() {
  const { data, loading, error, reload, setData } = useAsync(() => api.listUsers(), []);
  const [drawer, setDrawer] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? undefined} onRetry={reload} />;

  const planName = (id: string) => data.plans.find((p) => p.id === id)?.name ?? id;
  const groupName = (id: string) => data.groups.find((g) => g.id === id)?.name ?? id;

  async function save(input: UserInput) {
    if (editing) {
      const next = await api.updateUser(editing.id, input);
      setData((prev) => prev ? { ...prev, users: prev.users.map((u) => (u.id === next.id ? next : u)) } : prev);
      toast.success(t.users.updated);
      setEditing(null);
      return;
    }
    const created = await api.createUser(input);
    setData((prev) => prev ? { ...prev, users: [created, ...prev.users] } : prev);
    toast.success(t.users.created);
  }

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
    {
      key: "a",
      header: t.common.actions,
      render: (u) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon"><MoreHorizontal /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onSelect={() => { setEditing(u); setDrawer(true); }}>{t.common.edit}</DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                const next = await api.updateUser(u.id, { status: u.status === "active" ? "suspended" : "active" });
                setData((prev) => prev ? { ...prev, users: prev.users.map((x) => (x.id === next.id ? next : x)) } : prev);
                toast.success(t.users.toggled);
              }}
            >
              {u.status === "active" ? t.users.suspend : t.users.resume}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  const groupCols: Column<Group>[] = [
    { key: "n", header: t.common.name, render: (g) => g.name },
    { key: "m", header: t.users.members, render: (g) => g.memberCount },
    { key: "p", header: t.users.plans, render: (g) => planName(g.planId) },
    { key: "s", header: t.users.spend, render: (g) => <span className="font-mono">{formatUsd(g.spend)}</span> },
  ];

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader
        title={t.users.title}
        subtitle={t.users.subtitle}
        actions={
          <Button onClick={() => { setEditing(null); setDrawer(true); }}>
            <Plus />
            {t.users.add}
          </Button>
        }
      />
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
      <UserDrawer
        open={drawer}
        onOpenChange={setDrawer}
        initial={editing}
        groups={data.groups}
        plans={data.plans}
        onSubmit={save}
      />
    </div>
  );
}

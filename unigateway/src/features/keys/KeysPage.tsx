"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MoreHorizontal, Plus } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { ApiKeyDialog } from "@/components/keys/ApiKeyDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { formatDate, formatUsd } from "@/lib/format";
import type { ApiKey, ApiKeyInput, CreatedApiKey } from "@/types";

export function KeysPage() {
  const { data, loading, error, reload, setData } = useAsync(() => api.listKeys(), []);
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState<CreatedApiKey | null>(null);
  const params = useSearchParams();
  useEffect(() => {
    if (params.get("new") === "1") {
      setCreated(null);
      setOpen(true);
    }
  }, [params]);

  const columns: Column<ApiKey>[] = [
    { key: "name", header: t.common.name, render: (k) => k.name },
    { key: "mask", header: t.keys.masked, render: (k) => <span className="font-mono text-[11px]">{k.maskedKey}</span> },
    { key: "owner", header: t.keys.owner, render: (k) => k.owner },
    {
      key: "models",
      header: t.keys.models,
      render: (k) => <span className="font-mono text-[11px]">{k.allowedModels.join(", ")}</span>,
    },
    {
      key: "used",
      header: t.keys.used,
      render: (k) => (
        <span className="font-mono">
          {formatUsd(k.used)} / {formatUsd(k.budget)}
        </span>
      ),
    },
    { key: "rpm", header: t.keys.rpm, render: (k) => <span className="font-mono">{k.rpm}</span> },
    { key: "tpm", header: t.keys.tpm, render: (k) => <span className="font-mono">{k.tpm.toLocaleString()}</span> },
    { key: "created", header: t.common.created, render: (k) => formatDate(k.createdAt) },
    { key: "exp", header: t.keys.expires, render: (k) => (k.expiresAt ? formatDate(k.expiresAt) : t.keys.never) },
    {
      key: "st",
      header: t.common.status,
      render: (k) => (
        <Badge tone={k.status === "active" ? "success" : k.status === "expired" ? "error" : "neutral"}>{k.status}</Badge>
      ),
    },
    {
      key: "a",
      header: t.common.actions,
      render: (k) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem
              onSelect={async () => {
                await navigator.clipboard.writeText(k.maskedKey);
                toast.success(t.common.copied);
              }}
            >
              {t.common.copy}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                const next = await api.disableKey(k.id);
                setData((prev) => (prev ?? []).map((x) => (x.id === next.id ? next : x)));
                toast.success(t.keys.disabled);
              }}
            >
              {k.status === "active" ? t.common.disable : t.common.enable}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                const next = await api.regenerateKey(k.id);
                setData((prev) => (prev ?? []).map((x) => (x.id === next.id ? next : x)));
                setCreated(next);
                setOpen(true);
                toast.success(t.keys.regenerated);
              }}
            >
              {t.keys.regenerate}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={async () => {
                if (!confirm(t.keys.confirmDelete)) return;
                await api.deleteKey(k.id);
                setData((prev) => (prev ?? []).filter((x) => x.id !== k.id));
                toast.success(t.keys.deleted);
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
  if (error || !data) return <ErrorState message={error ?? undefined} onRetry={reload} />;

  return (
    <div className="mx-auto max-w-[1280px] space-y-4 p-5 md:p-6">
      <PageHeader
        title={t.keys.title}
        subtitle={t.keys.subtitle}
        actions={
          <Button
            onClick={() => {
              setCreated(null);
              setOpen(true);
            }}
          >
            <Plus />
            {t.keys.create}
          </Button>
        }
      />
      <DataTable columns={columns} rows={data} />
      <ApiKeyDialog
        open={open}
        onOpenChange={(v) => {
          setOpen(v);
          if (!v) setCreated(null);
        }}
        created={created}
        onCreate={async (input: ApiKeyInput) => {
          const next = await api.createKey(input);
          setData((prev) => [next, ...(prev ?? [])]);
          setCreated(next);
          toast.success(t.keys.created);
        }}
      />
    </div>
  );
}

"use client";

import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatLatency, formatNumber, formatUsd } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { RequestLog } from "@/types";

export function LogDetailDrawer({
  log,
  providerName,
  onClose,
}: {
  log: RequestLog | null;
  providerName: string;
  onClose: () => void;
}) {
  return (
    <Sheet open={!!log} onOpenChange={(o) => !o && onClose()}>
      <SheetContent title={t.logs.detail} description={log?.requestId}>
        {log && (
          <dl className="space-y-2 text-[12px]">
            <Row k={t.logs.time} v={formatDateTime(log.time)} />
            <Row k={t.logs.user} v={log.user} />
            <Row k={t.logs.key} v={log.keyName} />
            <Row k={t.logs.model} v={log.model} />
            <Row k={t.logs.provider} v={providerName} />
            <Row k={t.logs.prompt} v={formatNumber(log.promptTokens)} />
            <Row k={t.logs.completion} v={formatNumber(log.completionTokens)} />
            <Row k={t.logs.cost} v={formatUsd(log.cost, 4)} />
            <Row k={t.logs.latency} v={formatLatency(log.latency)} />
            <Row k={t.logs.endpoint} v={log.endpoint} />
            <div className="flex items-center justify-between border-b border-border py-1.5">
              <dt className="text-muted-foreground">{t.common.status}</dt>
              <dd>
                <Badge tone={log.status === "success" ? "success" : "error"}>{log.status}</Badge>
              </dd>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <dt className="text-muted-foreground">{t.logs.stream}</dt>
              <dd>{log.stream ? "true" : "false"}</dd>
            </div>
            {log.errorMessage && (
              <div className="rounded-sm border border-border bg-muted/40 p-2 font-mono text-[11px]">{log.errorMessage}</div>
            )}
          </dl>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border py-1.5">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="font-mono">{v}</dd>
    </div>
  );
}

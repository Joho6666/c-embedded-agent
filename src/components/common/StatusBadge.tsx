import { Badge } from "@/components/ui/badge";
import type { CredentialStatus, ProviderStatus, RequestStatusCode } from "@/types";

const credMap: Record<CredentialStatus, { label: string; tone: React.ComponentProps<typeof Badge>["tone"] }> = {
  healthy: { label: "Healthy", tone: "success" },
  rate_limited: { label: "Rate Limited", tone: "limit" },
  cooling: { label: "Cooling", tone: "cool" },
  circuit_open: { label: "Circuit Open", tone: "error" },
  unauthorized: { label: "Unauthorized", tone: "error" },
  quota_exhausted: { label: "Quota Exhausted", tone: "warning" },
  quota_daily_exhausted: { label: "Daily Quota", tone: "warning" },
  quota_monthly_exhausted: { label: "Monthly Quota", tone: "warning" },
  disabled: { label: "Disabled", tone: "neutral" },
  error: { label: "Error", tone: "error" },
};

const provMap: Record<ProviderStatus, { label: string; tone: React.ComponentProps<typeof Badge>["tone"] }> = {
  operational: { label: "Operational", tone: "success" },
  degraded: { label: "Degraded", tone: "warning" },
  partial_outage: { label: "Partial Outage", tone: "error" },
  down: { label: "Down", tone: "error" },
  offline: { label: "Offline", tone: "neutral" },
};

export function CredStatus({ status }: { status: CredentialStatus }) {
  const m = credMap[status] ?? { label: status, tone: "neutral" as const };
  return <Badge tone={m.tone}>{m.label}</Badge>;
}

export function ProvStatus({ status }: { status: ProviderStatus }) {
  const m = provMap[status];
  return <Badge tone={m.tone}>{m.label}</Badge>;
}

const lifecycle: Record<string, { label: string; tone: React.ComponentProps<typeof Badge>["tone"] }> = {
  pending: { label: "Pending", tone: "neutral" },
  routing: { label: "Routing", tone: "info" },
  connecting: { label: "Connecting", tone: "info" },
  streaming: { label: "Streaming", tone: "info" },
  ok: { label: "Completed", tone: "success" },
  error: { label: "Failed", tone: "error" },
  cancelled: { label: "Cancelled", tone: "warning" },
};

export function RequestStatus({ status, requestStatus }: { status: RequestStatusCode; requestStatus?: string }) {
  const life = requestStatus ? lifecycle[requestStatus] : undefined;
  if (life && requestStatus !== "ok") {
    return <Badge tone={life.tone}>{life.label}</Badge>;
  }
  const ok = status === 200 || status === "ok";
  const warn = status === 429 || status === "quota_exhausted" || status === "timeout" || status === "cancelled";
  const label = life ? life.label : String(status).toUpperCase();
  return (
    <Badge tone={ok ? "success" : warn ? "warning" : status === "pending" || status === "streaming" ? "info" : "error"} className="font-mono">
      {label}
    </Badge>
  );
}

export function Dot({ tone = "success" }: { tone?: "success" | "warning" | "error" | "neutral" | "info" }) {
  const map = {
    success: "bg-success",
    warning: "bg-warning",
    error: "bg-error",
    neutral: "bg-muted-foreground",
    info: "bg-info",
  };
  return <span className={`inline-block size-1.5 rounded-full ${map[tone]}`} />;
}

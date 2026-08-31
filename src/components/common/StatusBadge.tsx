import { Badge } from "@/components/ui/badge";
import type { CredentialStatus, ProviderStatus, RequestStatusCode } from "@/types";

const credMap: Record<CredentialStatus, { label: string; tone: React.ComponentProps<typeof Badge>["tone"] }> = {
  healthy: { label: "Healthy", tone: "success" },
  rate_limited: { label: "Rate Limited", tone: "limit" },
  cooling: { label: "Cooling", tone: "cool" },
  circuit_open: { label: "Circuit Open", tone: "error" },
  unauthorized: { label: "Unauthorized", tone: "error" },
  quota_exhausted: { label: "Quota Exhausted", tone: "warning" },
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
  const m = credMap[status];
  return <Badge tone={m.tone}>{m.label}</Badge>;
}

export function ProvStatus({ status }: { status: ProviderStatus }) {
  const m = provMap[status];
  return <Badge tone={m.tone}>{m.label}</Badge>;
}

export function RequestStatus({ status }: { status: RequestStatusCode }) {
  const ok = status === 200;
  const warn = status === 429 || status === "quota_exhausted" || status === "timeout";
  return (
    <Badge tone={ok ? "success" : warn ? "warning" : "error"} className="font-mono">
      {String(status).toUpperCase()}
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

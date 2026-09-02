import { cn } from "@/lib/utils";
import type { CapabilityStatus, DevicePresence, InstallStatus, SupportStatus } from "@/types/status";

const TONE: Record<string, string> = {
  pass: "bg-success",
  fail: "bg-error",
  partial: "bg-warning",
  unknown: "bg-muted-foreground",
  unavailable: "bg-muted-foreground/60",
  not_tested: "bg-muted-foreground/60",
  available: "bg-success",
  not_installed: "bg-error",
  not_configured: "bg-warning",
  supported: "bg-success",
  experimental: "bg-warning",
  planned: "bg-muted-foreground",
  connected: "bg-success",
  not_detected: "bg-muted-foreground",
};

export function StatusDot({
  status,
  className,
}: {
  status: CapabilityStatus | InstallStatus | SupportStatus | DevicePresence | string;
  className?: string;
}) {
  return <span className={cn("inline-block size-1.5 shrink-0 rounded-full", TONE[status] ?? "bg-muted-foreground", className)} />;
}

import { cn } from "@/lib/utils";

const map = {
  ready: { label: "Ready", cls: "text-muted-foreground bg-muted" },
  working: { label: "Working", cls: "text-info bg-info/10" },
  success: { label: "Success", cls: "text-success bg-success/10" },
  passed: { label: "Passed", cls: "text-success bg-success/10" },
  warning: { label: "Warning", cls: "text-warning bg-warning/10" },
  error: { label: "Error", cls: "text-error bg-error/10" },
  failed: { label: "Failed", cls: "text-error bg-error/10" },
  pending: { label: "Pending", cls: "text-muted-foreground bg-muted" },
  running: { label: "Running", cls: "text-info bg-info/10" },
  connected: { label: "Connected", cls: "text-success bg-success/10" },
  disconnected: { label: "Disconnected", cls: "text-muted-foreground bg-muted" },
  idle: { label: "Idle", cls: "text-muted-foreground bg-muted" },
  complete: { label: "Complete", cls: "text-success bg-success/10" },
  stopped: { label: "Stopped", cls: "text-warning bg-warning/10" },
} as const;

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: keyof typeof map | string;
  label?: string;
  className?: string;
}) {
  const item = map[status as keyof typeof map];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-medium tracking-wide",
        item?.cls ?? "bg-muted text-muted-foreground",
        className,
      )}
    >
      {label ?? item?.label ?? status}
    </span>
  );
}

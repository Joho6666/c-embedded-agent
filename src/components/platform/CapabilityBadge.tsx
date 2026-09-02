import { cn } from "@/lib/utils";
import type { SupportStatus } from "@/types/status";

const MAP: Record<SupportStatus, { label: string; cls: string }> = {
  supported: { label: "Beta", cls: "text-success bg-success/10" },
  experimental: { label: "Experimental", cls: "text-warning bg-warning/10" },
  planned: { label: "Planned", cls: "text-muted-foreground bg-muted" },
};

export function CapabilityBadge({
  status,
  label,
  className,
}: {
  status: SupportStatus;
  label?: string;
  className?: string;
}) {
  const item = MAP[status];
  return (
    <span className={cn("inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-medium tracking-wide", item.cls, className)}>
      {label ?? item.label}
    </span>
  );
}

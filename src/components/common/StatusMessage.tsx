import { StatusDot } from "./StatusDot";
import { cn } from "@/lib/utils";

export function StatusMessage({
  status,
  label,
  detail,
  className,
}: {
  status: string;
  label: string;
  detail?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start gap-2 text-[12px]", className)}>
      <StatusDot status={status} className="mt-1" />
      <div className="min-w-0">
        <div className="font-medium text-foreground">{label}</div>
        {detail ? <div className="text-[11px] text-muted-foreground">{detail}</div> : null}
      </div>
    </div>
  );
}

import { cn } from "@/lib/utils";

export function Progress({
  value,
  className,
  barClassName,
}: {
  value: number;
  className?: string;
  barClassName?: string;
}) {
  const v = Math.max(0, Math.min(100, value));
  const tone =
    v >= 100 ? "bg-error" : v >= 95 ? "bg-error" : v >= 90 ? "bg-warning" : v >= 80 ? "bg-orange-400" : "bg-success";
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-sm bg-muted", className)}>
      <div className={cn("h-full transition-all", barClassName ?? tone)} style={{ width: `${v}%` }} />
    </div>
  );
}

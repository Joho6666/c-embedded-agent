import { formatPercent } from "@/lib/utils";

export function MemoryUsage({
  label,
  used,
  total,
  unit = "KB",
}: {
  label: string;
  used: number;
  total: number;
  unit?: string;
}) {
  const pct = total ? (used / total) * 100 : 0;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-[12px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">
          {used} {unit} / {total} {unit}
          <span className="ml-2 text-muted-foreground">{formatPercent(used, total)}</span>
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-sm bg-muted">
        <div className="h-full bg-primary" style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

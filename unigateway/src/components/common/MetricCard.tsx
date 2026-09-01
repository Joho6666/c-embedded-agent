import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";
import { deltaLabel } from "@/lib/format";

export function MetricCard({
  label,
  value,
  delta,
  hint,
}: {
  label: string;
  value: string;
  delta?: number;
  hint?: string;
}) {
  return (
    <Card className="p-3.5">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-[20px] tracking-tight">{value}</div>
      {delta != null && (
        <div className={cn("mt-1 text-[11px]", delta >= 0 ? "text-success" : "text-error")}>
          {deltaLabel(delta)} {t.dashboard.vsYesterday}
        </div>
      )}
      {hint && <div className="mt-1 text-[11px] text-muted-foreground">{hint}</div>}
    </Card>
  );
}

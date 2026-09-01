import { Badge } from "@/components/ui/badge";
import { t } from "@/lib/i18n";
import type { HealthStatus } from "@/types";

const tone: Record<HealthStatus, "success" | "warning" | "error" | "neutral"> = {
  healthy: "success",
  degraded: "warning",
  error: "error",
  disabled: "neutral",
};

export function HealthBadge({ status }: { status: HealthStatus }) {
  return <Badge tone={tone[status]}>{t.health[status]}</Badge>;
}

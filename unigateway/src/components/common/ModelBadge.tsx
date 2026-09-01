import { Badge } from "@/components/ui/badge";
import { t } from "@/lib/i18n";
import type { ModelCapability } from "@/types";

export function ModelBadge({ cap }: { cap: ModelCapability }) {
  const tone = cap === "reasoning" || cap === "tools" ? "info" : "neutral";
  return <Badge tone={tone}>{t.cap[cap]}</Badge>;
}

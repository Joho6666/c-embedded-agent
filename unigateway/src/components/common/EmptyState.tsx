import { t } from "@/lib/i18n";

export function EmptyState({ title, hint }: { title?: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-[13px] text-foreground">{title ?? t.common.empty}</div>
      <div className="mt-1 text-[12px] text-muted-foreground">{hint ?? t.common.emptyHint}</div>
    </div>
  );
}

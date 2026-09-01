import { Button } from "@/components/ui/button";
import { t } from "@/lib/i18n";

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <div className="text-[13px]">{t.common.error}</div>
      <div className="text-[12px] text-muted-foreground">{message}</div>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          {t.common.retry}
        </Button>
      )}
    </div>
  );
}

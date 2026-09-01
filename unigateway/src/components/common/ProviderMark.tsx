import { cn } from "@/lib/utils";
import type { ProviderTemplate } from "@/types";

const marks: Record<ProviderTemplate, string> = {
  openai: "OA",
  anthropic: "AN",
  gemini: "GM",
  openrouter: "OR",
  newapi: "NA",
  oneapi: "OH",
  custom: "CU",
};

export function ProviderMark({ type, className }: { type: ProviderTemplate; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex size-6 items-center justify-center rounded-sm border border-border bg-muted font-mono text-[10px] tracking-tight",
        className,
      )}
    >
      {marks[type]}
    </span>
  );
}

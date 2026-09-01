import type { PatchWhy } from "@/types/patch";

export function PatchWhyView({ why }: { why?: PatchWhy }) {
  if (!why?.summary) return null;
  return (
    <div className="border-b border-border bg-panel px-3 py-1.5 text-[11px]">
      <span className="text-muted-foreground">Why · </span>
      {why.summary}
      {why.sources.length ? <span className="ml-2 text-muted-foreground">{why.sources.join(" · ")}</span> : null}
    </div>
  );
}

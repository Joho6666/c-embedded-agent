import { formatPricePerM } from "@/lib/format";

export function PriceBadge({ input, output }: { input: number; output: number }) {
  return (
    <span className="font-mono text-[11px] text-muted-foreground">
      {formatPricePerM(input)}
      {output > 0 ? ` · ${formatPricePerM(output)}` : ""}
    </span>
  );
}

import type { BenchmarkSummary } from "@/types/benchmark";

export function ReliabilityPanel({ data }: { data?: BenchmarkSummary | null }) {
  const value =
    data?.compileSuccess != null ? `${Math.round(data.compileSuccess * 100)}%` : "Not Tested";
  return (
    <div className="rounded-md border border-border bg-panel p-3.5">
      <div className="text-[11px] text-muted-foreground">Agent Reliability</div>
      <div className="mt-1 font-mono text-[22px] tracking-tight">{value}</div>
      <div className="mt-1 text-[11px] text-muted-foreground">{data?.mcu ?? "STM32F103"}</div>
    </div>
  );
}

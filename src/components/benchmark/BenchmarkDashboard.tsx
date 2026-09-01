import type { BenchmarkSummary } from "@/types/benchmark";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";

function pct(v: number | null | undefined) {
  if (v == null) return "No benchmark data";
  return `${Math.round(v * 100)}%`;
}

export function BenchmarkDashboardView({ data }: { data: BenchmarkSummary }) {
  if (!data.available) {
    return <CapabilityBanner reason={data.reason} />;
  }
  const tiles = [
    ["Tasks", data.tasks == null ? "—" : String(data.tasks)],
    ["Compile Success", pct(data.compileSuccess)],
    ["First Build Success", pct(data.firstBuildSuccess)],
    ["Auto Fix", pct(data.autoFix)],
    ["Average Iterations", data.avgIterations == null ? "—" : String(data.avgIterations)],
  ];
  return (
    <div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        {tiles.map(([k, v]) => (
          <div key={k} className="rounded-md border border-border bg-panel p-3">
            <div className="text-[11px] text-muted-foreground">{k}</div>
            <div className="mt-1 font-mono text-[18px]">{v}</div>
          </div>
        ))}
      </div>
      {data.reason && <p className="mt-3 text-[12px] text-muted-foreground">{data.reason}</p>}
      <h2 className="mt-6 text-[13px] font-medium">By Skill</h2>
      {data.bySkill.length === 0 ? (
        <p className="mt-2 text-[12px] text-muted-foreground">No benchmark data</p>
      ) : (
        <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-5">
          {data.bySkill.map((s) => (
            <div key={s.skillId} className="rounded-md border border-border bg-panel p-3">
              <div className="text-[12px]">{s.name}</div>
              <div className="font-mono text-[16px]">{s.tested && s.compileSuccess != null ? `${Math.round(s.compileSuccess * 100)}%` : "Not Tested"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

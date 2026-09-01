import type { ModelComparisonRow } from "@/types/benchmark";

export function ModelComparison({ rows }: { rows: ModelComparisonRow[] }) {
  return (
    <div>
      <h2 className="text-[13px] font-medium">Model Comparison</h2>
      {rows.length === 0 ? (
        <p className="mt-2 text-[12px] text-muted-foreground">No benchmark data</p>
      ) : (
        <div className="mt-2 overflow-hidden rounded-md border border-border">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-panel-2 text-[11px] text-muted-foreground">
              <tr>
                <th className="px-2 py-1.5">Model</th>
                <th className="px-2 py-1.5">Compile</th>
                <th className="px-2 py-1.5">Tokens</th>
                <th className="px-2 py-1.5">Cost</th>
                <th className="px-2 py-1.5">Iterations</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.model} className="odd:bg-panel">
                  <td className="px-2 py-1.5">{r.model}</td>
                  <td className="px-2 py-1.5 font-mono">{r.compileSuccess == null ? "—" : `${Math.round(r.compileSuccess * 100)}%`}</td>
                  <td className="px-2 py-1.5 font-mono">{r.tokens ?? "—"}</td>
                  <td className="px-2 py-1.5 font-mono">{r.cost ?? "—"}</td>
                  <td className="px-2 py-1.5 font-mono">{r.iterations ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

import type { ErrorMemoryEntry } from "@/types/memory";

export function ErrorMemoryDetailView({ item }: { item: ErrorMemoryEntry }) {
  return (
    <div className="space-y-4 text-[12px]">
      <section className="rounded-md border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Error Pattern</div>
        <div className="mt-1 font-mono text-[13px]">{item.pattern}</div>
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Root Cause</h2>
        <p className="mt-1 text-muted-foreground">{item.rootCause}</p>
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Fix Strategy</h2>
        <p className="mt-1">{item.fix}</p>
        {item.strategy?.length ? (
          <ol className="mt-2 list-decimal pl-4 text-muted-foreground">
            {item.strategy.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        ) : null}
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Affected Files</h2>
        <div className="mt-1 font-mono text-muted-foreground">{item.files.join(" · ") || "—"}</div>
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Knowledge Used</h2>
        <div className="mt-1 text-muted-foreground">{item.knowledge.join(" · ") || "—"}</div>
      </section>
      <section className="grid grid-cols-2 gap-2 md:grid-cols-4">
        {[
          ["MCU", item.mcu],
          ["Framework", item.framework ?? "—"],
          ["Successful Runs", String(item.successfulRuns)],
          ["Failed Runs", String(item.failedRuns)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-md border border-border bg-panel p-3">
            <div className="text-[11px] text-muted-foreground">{k}</div>
            <div className="mt-1 font-mono">{v}</div>
          </div>
        ))}
      </section>
      <div className="text-[11px] text-muted-foreground">
        Success Rate: {item.successRate == null || item.occurrences === 0 ? "Not Tested" : `${Math.round(item.successRate * 100)}%`} · Occurrences {item.occurrences}
      </div>
    </div>
  );
}

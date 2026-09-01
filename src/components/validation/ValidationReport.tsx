import type { ValidationResult } from "@/types/validation";
import { StatusBadge } from "@/components/common/StatusBadge";

export function ValidationReport({ result }: { result: ValidationResult }) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <section className="rounded-md border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Expected Behavior</div>
        <pre className="mt-2 whitespace-pre-wrap font-mono text-[12px]">{result.expected}</pre>
      </section>
      <section className="rounded-md border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Actual Behavior</div>
        <pre className="mt-2 whitespace-pre-wrap font-mono text-[12px]">{result.observed}</pre>
      </section>
      <section className="rounded-md border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Validation Result</div>
        <div className="mt-2 flex items-center gap-2">
          <StatusBadge status={result.status} />
          <span className="font-mono text-[12px]">
            Confidence {result.confidence == null ? "—" : `${Math.round(result.confidence * 100)}%`}
          </span>
        </div>
        <div className="mt-2 text-[12px] text-muted-foreground">{result.requirement}</div>
        {result.evidence && <div className="mt-2 text-[11px] text-muted-foreground">{result.evidence}</div>}
      </section>
    </div>
  );
}

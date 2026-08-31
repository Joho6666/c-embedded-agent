"use client";

import { problems as mockProblems } from "@/lib/mock/build";
import { useWorkspace } from "@/lib/stores/workspace";
import { Button } from "@/components/ui/button";
import type { Problem } from "@/types/build";
import { cn } from "@/lib/utils";

export function ProblemList({ items }: { items?: Problem[] }) {
  const problemsActive = useWorkspace((s) => s.problemsActive);
  const startDemo = useWorkspace((s) => s.startDemo);
  const list = items ?? (problemsActive ? mockProblems : mockProblems.filter((p) => p.severity === "warning"));
  const errors = list.filter((p) => p.severity === "error").length;
  const warnings = list.filter((p) => p.severity === "warning").length;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5 text-[11px]">
        <span>
          Problems · <span className="text-error">{errors} Errors</span> ·{" "}
          <span className="text-warning">{warnings} Warnings</span>
        </span>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" onClick={startDemo}>
            Ask Agent
          </Button>
          <Button size="sm">Fix All</Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {list.map((p) => (
          <div key={p.id} className="border-b border-border/70 px-3 py-2">
            <div className="flex items-center gap-2 text-[12px]">
              <span className={cn("font-medium", p.severity === "error" ? "text-error" : "text-warning")}>
                {p.severity === "error" ? "✕" : "⚠"} {p.file}:{p.line}
              </span>
              <span>{p.message}</span>
            </div>
            {p.suggestion && (
              <div className="mt-1 text-[11px] text-muted-foreground">Agent Fix：{p.suggestion}</div>
            )}
            <div className="mt-1.5 flex gap-1">
              <Button size="sm" variant="outline">
                Ask Agent
              </Button>
              <Button size="sm" variant="secondary">
                Fix
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

import type { PlanStep } from "@/types/agent";
import { cn } from "@/lib/utils";

export function PlanViewer({ plan }: { plan: PlanStep[] }) {
  return (
    <div className="flex flex-col">
      <div className="border-b border-border px-3 py-2 text-[11px] font-medium text-muted-foreground">执行计划</div>
      <ol className="p-2">
        {plan.map((p) => (
          <li key={p.id} className="flex items-start gap-2 px-2 py-1.5 text-[12px]">
            <span
              className={cn(
                "mt-1 size-1.5 shrink-0 rounded-full",
                p.status === "success" && "bg-success",
                p.status === "running" && "pulse-dot bg-info",
                p.status === "failed" && "bg-error",
                p.status === "pending" && "bg-zinc-600",
              )}
            />
            <span className="w-4 text-muted-foreground">{p.index}</span>
            <span className={cn(p.status === "pending" && "text-muted-foreground")}>{p.title}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

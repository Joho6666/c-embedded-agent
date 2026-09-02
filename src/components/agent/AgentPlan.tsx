import type { PlanStep } from "@/types/agent";
import { StatusBadge } from "@/components/common/StatusBadge";
import { cn } from "@/lib/utils";

const DEFAULT_PLAN: PlanStep[] = [
  { id: "req", index: 1, title: "分析需求", status: "pending" },
  { id: "hw", index: 2, title: "检查硬件上下文", status: "pending" },
  { id: "gen", index: 3, title: "生成代码", status: "pending" },
  { id: "build", index: 4, title: "编译", status: "pending" },
  { id: "diag", index: 5, title: "Diagnostics", status: "pending" },
  { id: "fix", index: 6, title: "Auto Fix", status: "pending" },
  { id: "rebuild", index: 7, title: "Rebuild", status: "pending" },
  { id: "flash", index: 8, title: "Flash", status: "pending" },
  { id: "validate", index: 9, title: "Hardware Validate", status: "pending" },
];

export function AgentPlan({ plan }: { plan?: PlanStep[] }) {
  const steps = plan?.length ? plan : DEFAULT_PLAN;
  return (
    <ol className="space-y-1 p-2">
      {steps.map((p) => (
        <li key={p.id} className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-[12px]">
          <span
            className={cn(
              "size-1.5 shrink-0 rounded-full",
              p.status === "success" && "bg-success",
              p.status === "running" && "pulse-dot bg-info",
              p.status === "failed" && "bg-error",
              p.status === "pending" && "bg-zinc-600",
            )}
          />
          <span className={cn("flex-1", p.status === "pending" && "text-muted-foreground")}>{p.title}</span>
          <StatusBadge
            status={p.status === "success" ? "pass" : p.status === "failed" ? "fail" : p.status === "running" ? "running" : "pending"}
          />
        </li>
      ))}
    </ol>
  );
}

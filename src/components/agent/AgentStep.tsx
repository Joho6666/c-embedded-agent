import { Check, Circle, Loader2, X } from "lucide-react";
import type { AgentStep as AgentStepT } from "@/types/agent";
import { cn } from "@/lib/utils";
import { ToolCallCard } from "./ToolCallCard";

export function AgentStep({ step }: { step: AgentStepT }) {
  return (
    <div className="relative pl-6">
      <span className="absolute left-0 top-1">
        {step.status === "success" && <Check className="size-3.5 text-success" />}
        {step.status === "running" && <Loader2 className="size-3.5 animate-spin text-info" />}
        {step.status === "failed" && <X className="size-3.5 text-error" />}
        {step.status === "pending" && <Circle className="size-3.5 text-muted-foreground" />}
      </span>
      <div className="text-[13px] font-medium">{step.title}</div>
      {step.detail && (
        <div className={cn("mt-0.5 text-[12px] text-muted-foreground", step.status === "failed" && "text-error")}>
          {step.detail}
        </div>
      )}
      {step.files && (
        <div className="mt-1 flex flex-wrap gap-1">
          {step.files.map((f) => (
            <span key={f} className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[11px]">
              {f}
            </span>
          ))}
        </div>
      )}
      {step.toolCall && <ToolCallCard call={step.toolCall} />}
    </div>
  );
}

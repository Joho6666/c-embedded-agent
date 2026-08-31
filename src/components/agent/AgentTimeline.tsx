import type { AgentStep as AgentStepT } from "@/types/agent";
import { AgentStep } from "./AgentStep";

export function AgentTimeline({ steps }: { steps: AgentStepT[] }) {
  if (steps.length === 0) {
    return (
      <div className="rounded-sm border border-dashed border-border p-6 text-[12px] text-muted-foreground">
        尚未开始。输入任务后点击 Run Agent，或运行 STM32 LED Demo。
      </div>
    );
  }
  return (
    <div className="space-y-4 border-l border-border ml-1.5">
      {steps.map((s) => (
        <div key={s.id} className="-ml-1.5">
          <AgentStep step={s} />
        </div>
      ))}
    </div>
  );
}

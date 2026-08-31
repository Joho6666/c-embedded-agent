"use client";

import { AgentTimeline } from "@/components/agent/AgentTimeline";
import { TaskInput } from "@/components/agent/TaskInput";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/lib/stores/workspace";
import { DEMO_PROMPT } from "@/lib/mock/demo";

export default function AgentPage() {
  const steps = useWorkspace((s) => s.steps);
  const startDemo = useWorkspace((s) => s.startDemo);
  const setPrompt = useWorkspace((s) => s.setPrompt);
  const prompt = useWorkspace((s) => s.prompt);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border bg-panel px-4 py-2">
        <div>
          <div className="text-[11px] text-muted-foreground">任务</div>
          <div className="text-[13px] font-medium">{prompt || DEMO_PROMPT}</div>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            setPrompt(DEMO_PROMPT);
            startDemo();
          }}
        >
          STM32 LED Demo
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="mb-3 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Agent Timeline
        </div>
        <AgentTimeline steps={steps} />
      </div>
      <TaskInput />
    </div>
  );
}

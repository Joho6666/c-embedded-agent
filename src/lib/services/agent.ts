import { sleep } from "@/lib/utils";
import { historyTasks } from "@/lib/mock/build";
import { DEMO_PROMPT } from "@/lib/mock/demo";
import type { AgentTask } from "@/types/agent";

export async function listAgentHistory(): Promise<AgentTask[]> {
  await sleep(50);
  return historyTasks;
}

export async function submitTask(prompt: string): Promise<{ id: string; prompt: string }> {
  await sleep(80);
  return { id: `run-${Date.now()}`, prompt: prompt || DEMO_PROMPT };
}

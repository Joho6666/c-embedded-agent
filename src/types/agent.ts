export type AgentMode = "auto" | "plan" | "code" | "debug";
export type AgentStatus = "ready" | "working" | "waiting_approval" | "error" | "stopped";
export type StepStatus = "pending" | "running" | "success" | "failed";

export interface PlanStep {
  id: string;
  index: number;
  title: string;
  status: StepStatus;
}

export interface AgentTask {
  id: string;
  title: string;
  prompt: string;
  status: "complete" | "working" | "failed";
  createdAt: string;
  projectName: string;
}

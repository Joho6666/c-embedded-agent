export type AgentStatus = "ready" | "working" | "error" | "stopped";
export type StepStatus = "pending" | "running" | "success" | "failed";
export type AgentMode = "auto" | "plan" | "code" | "debug";

export interface ToolCall {
  tool: string;
  command: string;
  result?: string;
  status: StepStatus;
}

export interface AgentStep {
  id: string;
  title: string;
  detail?: string;
  status: StepStatus;
  files?: string[];
  toolCall?: ToolCall;
}

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

import type { AgentMode, PlanStep } from "@/types/agent";
import type { AgentArtifact, AgentEvent } from "@/types/events";

export type AgentRunStatus =
  | "queued"
  | "planning"
  | "running"
  | "waiting_approval"
  | "success"
  | "failed"
  | "cancelled";

export interface TokenUsage {
  input: number;
  output: number;
}

export interface CreateRunInput {
  projectId: string;
  prompt: string;
  mode: AgentMode;
  goldenPath?: boolean;
}

export interface AgentRun {
  id: string;
  projectId: string;
  prompt: string;
  mode: AgentMode;
  status: AgentRunStatus;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
  events: AgentEvent[];
  artifacts: AgentArtifact[];
  plan: PlanStep[];
  currentStep?: string;
  error?: string;
  tokenUsage?: TokenUsage;
}

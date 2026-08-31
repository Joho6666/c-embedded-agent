import type { AgentApproval } from "@/types/events";
import type { AgentRun, CreateRunInput } from "@/types/run";
import type { AgentEvent } from "@/types/events";

export type ApprovalDecision = "approved" | "rejected" | "once" | "always";

export interface AgentBackend {
  createRun(input: CreateRunInput): Promise<AgentRun>;
  stopRun(runId: string): Promise<void>;
  approveAction(runId: string, approvalId: string, decision: ApprovalDecision): Promise<void>;
  listRuns(): Promise<AgentRun[]>;
  getRun(runId: string): Promise<AgentRun | undefined>;
  subscribeEvents(runId: string, onEvent: (e: AgentEvent) => void): () => void;
}

export type EventListener = (e: AgentEvent) => void;

export interface ApprovalWaiter {
  resolve: (decision: ApprovalDecision) => void;
}

export type { AgentApproval };

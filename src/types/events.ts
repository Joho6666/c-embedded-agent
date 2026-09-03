export type AgentEventType =
  | "reasoning"
  | "plan"
  | "knowledge_query"
  | "knowledge_result"
  | "tool_call"
  | "tool_result"
  | "file_read"
  | "file_write"
  | "file_diff"
  | "compile"
  | "diagnostic"
  | "test"
  | "flash"
  | "serial"
  | "validation"
  | "approval"
  | "error"
  | "pin_conflict"
  | "terminal"
  | "run_stopped"
  | "build_result";

export type AgentEventStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "cancelled"
  | "waiting_approval";

export type ArtifactKind =
  | "source_file"
  | "header_file"
  | "hex"
  | "bin"
  | "elf"
  | "map"
  | "log"
  | "report"
  | "datasheet"
  | "build_result"
  | "test_result";

export type RiskLevel = "safe" | "low" | "medium" | "high";

export interface AgentToolRef {
  name: string;
  command?: string;
  args?: Record<string, unknown>;
  exitCode?: number;
}

export interface KnowledgeSourceRef {
  title: string;
  uri?: string;
  page?: number;
  section?: string;
  score?: number;
}

export interface AgentArtifact {
  id: string;
  runId: string;
  kind: ArtifactKind;
  name: string;
  path?: string;
  mime?: string;
  size?: number;
  createdAt: string;
}

export interface AgentToolCall {
  id: string;
  runId: string;
  tool: string;
  command: string;
  status: AgentEventStatus;
  startedAt: string;
  finishedAt?: string;
  exitCode?: number;
  stdout?: string;
  stderr?: string;
}

export interface AgentDiagnostic {
  id: string;
    source: "gcc" | "ld" | "clangd" | "cppcheck" | "ceedling" | "agent";
  severity: "error" | "warning" | "info";
  path: string;
  line: number;
  column?: number;
  code?: string;
  message: string;
  suggestion?: string;
}

export interface AgentApproval {
  id: string;
  runId: string;
  eventId: string;
  title: string;
  summary: string;
  steps: string[];
  risk: RiskLevel;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
}

export interface AgentEvent {
  id: string;
  runId: string;
  parentId?: string;
  type: AgentEventType;
  status: AgentEventStatus;
  title: string;
  description?: string;
  timestamp: string;
  durationMs?: number;
  tool?: AgentToolRef;
  files?: string[];
  output?: string;
  original?: string;
  proposed?: string;
  before?: string;
  after?: string;
  stream?: "stdout" | "stderr";
  content?: string;
  path?: string;
  source?: KnowledgeSourceRef;
  artifacts?: AgentArtifact[];
  diagnostics?: AgentDiagnostic[];
  risk?: RiskLevel;
  requiresApproval?: boolean;
  approvalId?: string;
  plan?: import("@/types/agent").PlanStep[];
}

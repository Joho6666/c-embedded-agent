export type OsProjectStatus = "planned" | "active" | "paused" | "completed" | "archived";
export type OsTaskStatus = "todo" | "in_progress" | "agent_running" | "review" | "blocked" | "done";
export type OsAgentStatus = "idle" | "running" | "waiting" | "error" | "offline" | "planned";
export type OsPriority = "low" | "medium" | "high" | "urgent";
export type OsProjectKind = "firmware" | "general";
export type OsDocKind = "prd" | "design" | "note" | "agent_output";

export interface OsProject {
  id: string;
  workspaceId?: string;
  backendProjectId?: string | null;
  kind: OsProjectKind;
  name: string;
  description: string;
  status: OsProjectStatus;
  priority: OsPriority;
  deadline?: string | null;
  owner?: string;
  currentAgentId?: string | null;
  progress: number;
  createdAt: string;
  updatedAt: string;
}

export interface OsTask {
  id: string;
  projectId: string;
  title: string;
  description: string;
  status: OsTaskStatus;
  priority: OsPriority;
  dueAt?: string | null;
  assignee?: string;
  agentId?: string | null;
  runId?: string | null;
  parentId?: string | null;
  labels: string[];
  createdAt: string;
  updatedAt: string;
}

export interface OsAgent {
  id: string;
  name: string;
  provider: string;
  model?: string;
  type: string;
  description: string;
  capabilities: string[];
  status: OsAgentStatus;
  endpoint?: string;
  runnable: boolean;
}

export interface OsActivity {
  id: string;
  projectId?: string | null;
  taskId?: string | null;
  agentId?: string | null;
  runId?: string | null;
  actorType: "user" | "agent" | "system";
  verb: string;
  objectType: string;
  objectId?: string | null;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface OsDocument {
  id: string;
  projectId: string;
  title: string;
  kind: OsDocKind;
  body: string;
  createdAt: string;
}

export interface OsFile {
  path: string;
  source: "workspace" | "upload" | "github";
  mime?: string;
}

export interface OsToday {
  myTasks: OsTask[];
  agentRunning: OsTask[];
  needsReview: OsTask[];
  blocked: OsTask[];
  upcoming: OsTask[];
  recentActivity: OsActivity[];
  blockedProjects: OsProject[];
  focus: OsTask | null;
  counts: {
    attention: number;
    running: number;
    review: number;
    blocked: number;
  };
}

export const TASK_COLUMNS: OsTaskStatus[] = ["todo", "in_progress", "agent_running", "review", "blocked", "done"];

export const TASK_STATUS_LABEL: Record<OsTaskStatus, string> = {
  todo: "Todo",
  in_progress: "In Progress",
  agent_running: "Agent Running",
  review: "Review",
  blocked: "Blocked",
  done: "Done",
};

export const PROJECT_STATUS_LABEL: Record<OsProjectStatus, string> = {
  planned: "Planned",
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  archived: "Archived",
};

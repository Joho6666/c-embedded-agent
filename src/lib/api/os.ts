import { apiFetch, API_BASE } from "./client";
import { useLive } from "@/lib/stores/live-store";
import type { OsAgent, OsActivity, OsDocument, OsFile, OsProject, OsTask, OsToday } from "@/types/os";

export class OsApiError extends Error {
  status: number;
  code?: string;
  reason?: string;
  constructor(status: number, message: string, code?: string, reason?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.reason = reason;
  }
}

async function osFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let code: string | undefined;
    let reason: string | undefined;
    try {
      const body = (await res.json()) as { detail?: { code?: string; reason?: string } | string };
      if (typeof body.detail === "string") reason = body.detail;
      else if (body.detail && typeof body.detail === "object") {
        code = body.detail.code;
        reason = body.detail.reason;
      }
    } catch {
      reason = `${res.status} ${path}`;
    }
    throw new OsApiError(res.status, reason || `${res.status} ${path}`, code, reason);
  }
  return res.json() as Promise<T>;
}

export function osLive() {
  return useLive.getState().mode === "live";
}

export const osApi = {
  listProjects: () => osFetch<OsProject[]>("/api/os/projects"),
  createProject: (body: Partial<OsProject> & { name: string }) =>
    osFetch<OsProject>("/api/os/projects", { method: "POST", body: JSON.stringify(body) }),
  getProject: (id: string) => osFetch<OsProject>(`/api/os/projects/${id}`),
  patchProject: (id: string, body: Partial<OsProject>) =>
    osFetch<OsProject>(`/api/os/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  listTasks: (projectId: string) => osFetch<OsTask[]>(`/api/os/projects/${projectId}/tasks`),
  createTask: (projectId: string, body: Partial<OsTask> & { title: string }) =>
    osFetch<OsTask>(`/api/os/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(body) }),
  getTask: (id: string) => osFetch<OsTask>(`/api/os/tasks/${id}`),
  patchTask: (id: string, body: Partial<OsTask>) =>
    osFetch<OsTask>(`/api/os/tasks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  assignTask: (id: string, agentId: string) =>
    osFetch<{ task: OsTask; runId: string; agentId: string }>(`/api/os/tasks/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ agentId }),
    }),
  reviewTask: (id: string, decision: string) =>
    osFetch<{ task: OsTask }>(`/api/os/tasks/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),
  listAgents: () => osFetch<OsAgent[]>("/api/os/agents"),
  activity: (projectId?: string) =>
    osFetch<OsActivity[]>(`/api/os/activity${projectId ? `?projectId=${encodeURIComponent(projectId)}` : ""}`),
  today: () => osFetch<OsToday>("/api/os/today"),
  listDocuments: (projectId: string) => osFetch<OsDocument[]>(`/api/os/projects/${projectId}/documents`),
  createDocument: (projectId: string, body: Partial<OsDocument> & { title: string }) =>
    osFetch<OsDocument>(`/api/os/projects/${projectId}/documents`, { method: "POST", body: JSON.stringify(body) }),
  listFiles: (projectId: string) => osFetch<OsFile[]>(`/api/os/projects/${projectId}/files`),
};

export { apiFetch };

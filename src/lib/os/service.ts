import { OsApiError, osApi, osLive } from "@/lib/api/os";
import { demoToday, useOsStore } from "@/lib/stores/os-store";
import type { OsAgent, OsActivity, OsDocument, OsFile, OsProject, OsTask, OsToday } from "@/types/os";

export { OsApiError };

export async function loadToday(): Promise<OsToday> {
  if (osLive()) return osApi.today();
  useOsStore.getState().ensureSeed();
  return demoToday();
}

export async function loadProjects(): Promise<OsProject[]> {
  if (osLive()) return osApi.listProjects();
  useOsStore.getState().ensureSeed();
  return useOsStore.getState().projects;
}

export async function loadProject(id: string): Promise<OsProject | undefined> {
  if (osLive()) {
    try {
      return await osApi.getProject(id);
    } catch {
      return undefined;
    }
  }
  useOsStore.getState().ensureSeed();
  return useOsStore.getState().projects.find((p) => p.id === id);
}

export async function createProject(input: Partial<OsProject> & { name: string }): Promise<OsProject> {
  if (osLive()) return osApi.createProject(input);
  return useOsStore.getState().createProject(input);
}

export async function patchProject(id: string, patch: Partial<OsProject>): Promise<OsProject | undefined> {
  if (osLive()) return osApi.patchProject(id, patch);
  return useOsStore.getState().patchProject(id, patch);
}

export async function loadTasks(projectId: string): Promise<OsTask[]> {
  if (osLive()) return osApi.listTasks(projectId);
  return useOsStore.getState().tasks.filter((t) => t.projectId === projectId);
}

export async function createTask(projectId: string, input: Partial<OsTask> & { title: string }): Promise<OsTask> {
  if (osLive()) return osApi.createTask(projectId, input);
  return useOsStore.getState().createTask(projectId, input);
}

export async function patchTask(id: string, patch: Partial<OsTask>): Promise<OsTask | undefined> {
  if (osLive()) return osApi.patchTask(id, patch);
  return useOsStore.getState().patchTask(id, patch);
}

export async function assignTask(id: string, agentId: string): Promise<{ task: OsTask; runId?: string }> {
  if (osLive()) return osApi.assignTask(id, agentId);
  const store = useOsStore.getState();
  const task = store.tasks.find((t) => t.id === id);
  if (!task) throw new OsApiError(404, "task not found");
  const agent = store.agents.find((a) => a.id === agentId);
  if (!agent?.runnable) {
    throw new OsApiError(409, `${agent?.name ?? agentId} is planned and cannot execute in P0. Use C-Agent.`, "agent_unavailable");
  }
  const project = store.projects.find((p) => p.id === task.projectId);
  if (!project?.backendProjectId) {
    throw new OsApiError(409, "C-Agent needs a firmware workspace. Link backendProjectId first.", "no_firmware_workspace");
  }
  throw new OsApiError(
    409,
    "C-Agent execution needs a LIVE FastAPI backend. DEMO will not fake a successful run.",
    "live_required",
  );
}

export async function reviewTask(id: string, decision: string): Promise<OsTask | undefined> {
  if (osLive()) return (await osApi.reviewTask(id, decision)).task;
  const map: Record<string, OsTask["status"]> = {
    approved: "done",
    changes_requested: "in_progress",
    retry: "todo",
    rejected: "blocked",
  };
  const status = map[decision];
  if (!status) throw new OsApiError(400, "invalid decision");
  const next = useOsStore.getState().patchTask(id, { status });
  if (next) {
    useOsStore.getState().addActivity({
      projectId: next.projectId,
      taskId: id,
      actorType: "user",
      verb: "reviewed",
      objectType: "task",
      objectId: id,
      payload: { decision, status },
    });
  }
  return next;
}

export async function loadAgents(): Promise<OsAgent[]> {
  if (osLive()) return osApi.listAgents();
  return useOsStore.getState().agents;
}

export async function loadActivity(projectId?: string): Promise<OsActivity[]> {
  if (osLive()) return osApi.activity(projectId);
  const items = useOsStore.getState().activities;
  return projectId ? items.filter((a) => a.projectId === projectId) : items;
}

export async function loadDocuments(projectId: string): Promise<OsDocument[]> {
  if (osLive()) return osApi.listDocuments(projectId);
  return useOsStore.getState().documents.filter((d) => d.projectId === projectId);
}

export async function createDocument(projectId: string, input: Partial<OsDocument> & { title: string }): Promise<OsDocument> {
  if (osLive()) return osApi.createDocument(projectId, input);
  return useOsStore.getState().createDocument(projectId, input);
}

export async function loadFiles(projectId: string): Promise<OsFile[]> {
  if (osLive()) {
    try {
      return await osApi.listFiles(projectId);
    } catch {
      return [];
    }
  }
  return [];
}

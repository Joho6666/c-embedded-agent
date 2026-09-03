"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { uid } from "@/lib/utils";
import type { OsActivity, OsAgent, OsDocument, OsProject, OsTask, OsToday } from "@/types/os";

const nowIso = () => new Date().toISOString();

const seedAgents: OsAgent[] = [
  {
    id: "c-agent",
    name: "C-Agent",
    provider: "local-runtime",
    model: "configured-llm",
    type: "embedded",
    description: "STM32F103 HAL firmware agent.",
    capabilities: ["code", "compile", "flash", "serial"],
    status: "idle",
    runnable: true,
  },
  {
    id: "codex",
    name: "Codex",
    provider: "openai",
    type: "coding",
    description: "Planned. Not executable in P0.",
    capabilities: ["code"],
    status: "planned",
    runnable: false,
  },
  {
    id: "claude-code",
    name: "Claude Code",
    provider: "anthropic",
    type: "coding",
    description: "Planned. Not executable in P0.",
    capabilities: ["code"],
    status: "planned",
    runnable: false,
  },
  {
    id: "grok",
    name: "Grok",
    provider: "xai",
    type: "general",
    description: "Planned. Not executable in P0.",
    capabilities: ["general"],
    status: "planned",
    runnable: false,
  },
  {
    id: "custom",
    name: "Custom Agent",
    provider: "custom",
    type: "general",
    description: "Planned slot.",
    capabilities: [],
    status: "planned",
    runnable: false,
  },
];

function stampProject(): OsProject {
  const t = nowIso();
  return {
    id: uid("osp"),
    workspaceId: "default",
    backendProjectId: null,
    kind: "general",
    name: "MyOS onboarding",
    description: "First Work OS project. Create a task and assign C-Agent when a firmware workspace is linked.",
    status: "active",
    priority: "medium",
    owner: "user",
    currentAgentId: "c-agent",
    progress: 0,
    createdAt: t,
    updatedAt: t,
  };
}

function stampTask(projectId: string): OsTask {
  const t = nowIso();
  return {
    id: uid("tsk"),
    projectId,
    title: "Define first firmware task",
    description: "Link an STM32 workspace, then assign C-Agent.",
    status: "todo",
    priority: "high",
    assignee: "user",
    labels: ["onboarding"],
    createdAt: t,
    updatedAt: t,
  };
}

interface OsState {
  hydrated: boolean;
  projects: OsProject[];
  tasks: OsTask[];
  documents: OsDocument[];
  activities: OsActivity[];
  agents: OsAgent[];
  ensureSeed: () => void;
  addActivity: (partial: Omit<OsActivity, "id" | "createdAt">) => OsActivity;
  createProject: (input: Partial<OsProject> & { name: string }) => OsProject;
  patchProject: (id: string, patch: Partial<OsProject>) => OsProject | undefined;
  createTask: (projectId: string, input: Partial<OsTask> & { title: string }) => OsTask;
  patchTask: (id: string, patch: Partial<OsTask>) => OsTask | undefined;
  createDocument: (projectId: string, input: Partial<OsDocument> & { title: string }) => OsDocument;
  refreshProgress: (projectId: string) => void;
}

function progressOf(tasks: OsTask[], projectId: string) {
  const mine = tasks.filter((t) => t.projectId === projectId);
  if (!mine.length) return 0;
  return Math.round((100 * mine.filter((t) => t.status === "done").length) / mine.length);
}

export const useOsStore = create<OsState>()(
  persist(
    (set, get) => ({
      hydrated: false,
      projects: [],
      tasks: [],
      documents: [],
      activities: [],
      agents: seedAgents,
      ensureSeed: () => {
        if (get().projects.length) return;
        const project = stampProject();
        const task = stampTask(project.id);
        const act: OsActivity = {
          id: uid("act"),
          projectId: project.id,
          taskId: task.id,
          actorType: "system",
          verb: "created",
          objectType: "project",
          objectId: project.id,
          payload: { demo: true },
          createdAt: nowIso(),
        };
        set({ projects: [project], tasks: [task], activities: [act], agents: seedAgents });
      },
      addActivity: (partial) => {
        const item: OsActivity = { ...partial, id: uid("act"), createdAt: nowIso() };
        set((s) => ({ activities: [item, ...s.activities].slice(0, 200) }));
        return item;
      },
      createProject: (input) => {
        const t = nowIso();
        const project: OsProject = {
          id: uid("osp"),
          workspaceId: "default",
          backendProjectId: input.backendProjectId ?? null,
          kind: input.kind ?? "general",
          name: input.name,
          description: input.description ?? "",
          status: input.status ?? "active",
          priority: input.priority ?? "medium",
          deadline: input.deadline,
          owner: input.owner ?? "user",
          currentAgentId: input.currentAgentId ?? null,
          progress: 0,
          createdAt: t,
          updatedAt: t,
        };
        set((s) => ({ projects: [project, ...s.projects] }));
        get().addActivity({
          projectId: project.id,
          actorType: "user",
          verb: "created",
          objectType: "project",
          objectId: project.id,
          payload: { name: project.name },
        });
        return project;
      },
      patchProject: (id, patch) => {
        let next: OsProject | undefined;
        set((s) => ({
          projects: s.projects.map((p) => {
            if (p.id !== id) return p;
            next = { ...p, ...patch, id: p.id, updatedAt: nowIso() };
            return next;
          }),
        }));
        if (next) {
          get().addActivity({
            projectId: id,
            actorType: "user",
            verb: "updated",
            objectType: "project",
            objectId: id,
            payload: { fields: Object.keys(patch) },
          });
        }
        return next;
      },
      createTask: (projectId, input) => {
        const t = nowIso();
        const task: OsTask = {
          id: uid("tsk"),
          projectId,
          title: input.title,
          description: input.description ?? "",
          status: input.status ?? "todo",
          priority: input.priority ?? "medium",
          dueAt: input.dueAt,
          assignee: input.assignee ?? "user",
          agentId: input.agentId,
          labels: input.labels ?? [],
          createdAt: t,
          updatedAt: t,
        };
        set((s) => ({ tasks: [task, ...s.tasks] }));
        get().refreshProgress(projectId);
        get().addActivity({
          projectId,
          taskId: task.id,
          actorType: "user",
          verb: "created",
          objectType: "task",
          objectId: task.id,
          payload: { title: task.title },
        });
        return task;
      },
      patchTask: (id, patch) => {
        let next: OsTask | undefined;
        const prev = get().tasks.find((t) => t.id === id);
        set((s) => ({
          tasks: s.tasks.map((t) => {
            if (t.id !== id) return t;
            next = { ...t, ...patch, id: t.id, updatedAt: nowIso() };
            return next;
          }),
        }));
        if (next) {
          get().refreshProgress(next.projectId);
          if (patch.status && prev && patch.status !== prev.status) {
            get().addActivity({
              projectId: next.projectId,
              taskId: id,
              actorType: "user",
              verb: "status_changed",
              objectType: "task",
              objectId: id,
              payload: { from: prev.status, to: patch.status },
            });
          }
        }
        return next;
      },
      createDocument: (projectId, input) => {
        const doc: OsDocument = {
          id: uid("doc"),
          projectId,
          title: input.title,
          kind: input.kind ?? "note",
          body: input.body ?? "",
          createdAt: nowIso(),
        };
        set((s) => ({ documents: [doc, ...s.documents] }));
        get().addActivity({
          projectId,
          actorType: "user",
          verb: "created",
          objectType: "document",
          objectId: doc.id,
          payload: { title: doc.title },
        });
        return doc;
      },
      refreshProgress: (projectId) => {
        const value = progressOf(get().tasks, projectId);
        set((s) => ({
          projects: s.projects.map((p) => (p.id === projectId ? { ...p, progress: value, updatedAt: nowIso() } : p)),
        }));
      },
    }),
    {
      name: "myos-os",
      partialize: (s) => ({
        projects: s.projects,
        tasks: s.tasks,
        documents: s.documents,
        activities: s.activities,
      }),
    },
  ),
);

export function demoToday(): OsToday {
  const s = useOsStore.getState();
  s.ensureSeed();
  const tasks = useOsStore.getState().tasks;
  const activities = useOsStore.getState().activities;
  const projects = useOsStore.getState().projects;
  const myTasks = tasks.filter((t) => t.status === "todo" || t.status === "in_progress");
  const running = tasks.filter((t) => t.status === "agent_running");
  const review = tasks.filter((t) => t.status === "review");
  const blocked = tasks.filter((t) => t.status === "blocked");
  const upcoming = tasks.filter((t) => t.dueAt && t.status !== "done").slice(0, 8);
  const focus = review[0] ?? blocked[0] ?? running[0] ?? myTasks[0] ?? null;
  return {
    myTasks,
    agentRunning: running,
    needsReview: review,
    blocked,
    upcoming,
    recentActivity: activities.slice(0, 20),
    blockedProjects: projects.filter((p) => p.status === "paused"),
    focus,
    counts: {
      attention: myTasks.length + review.length + blocked.length,
      running: running.length,
      review: review.length,
      blocked: blocked.length,
    },
  };
}

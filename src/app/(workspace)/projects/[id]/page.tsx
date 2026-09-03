"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/common/Empty";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useLive } from "@/lib/stores/live-store";
import { useProject } from "@/lib/stores/project-store";
import { useAgent } from "@/lib/stores/agent-store";
import {
  OsApiError,
  assignTask,
  createDocument,
  createTask,
  loadActivity,
  loadAgents,
  loadDocuments,
  loadFiles,
  loadProject,
  loadTasks,
  patchProject,
  patchTask,
  reviewTask,
} from "@/lib/os/service";
import type { OsActivity, OsAgent, OsDocument, OsFile, OsProject, OsTask, OsTaskStatus } from "@/types/os";
import { PROJECT_STATUS_LABEL, TASK_COLUMNS, TASK_STATUS_LABEL } from "@/types/os";

const TABS = ["overview", "tasks", "docs", "files", "agents", "activity"] as const;
type Tab = (typeof TABS)[number];

export default function OsProjectPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const mode = useLive((s) => s.mode);
  const setFirmwareId = useProject((s) => s.setProjectId);
  const events = useAgent((s) => s.events);
  const activeRun = useAgent((s) => s.activeRun);
  const attachRun = useAgent((s) => s.attachRun);
  const setPrompt = useAgent((s) => s.setPrompt);
  const statusText = useAgent((s) => s.statusText);

  const id = params.id;
  const tab = (TABS.includes(search.get("tab") as Tab) ? search.get("tab") : "overview") as Tab;
  const selectedTaskId = search.get("task");

  const [project, setProject] = useState<OsProject | null>(null);
  const [tasks, setTasks] = useState<OsTask[]>([]);
  const [docs, setDocs] = useState<OsDocument[]>([]);
  const [files, setFiles] = useState<OsFile[]>([]);
  const [agents, setAgents] = useState<OsAgent[]>([]);
  const [activity, setActivity] = useState<OsActivity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [docBody, setDocBody] = useState("");
  const [assignError, setAssignError] = useState<string | null>(null);

  const selected = tasks.find((t) => t.id === selectedTaskId) ?? null;

  const reload = useCallback(async () => {
    const p = await loadProject(id);
    if (!p) {
      setProject(null);
      setError("project not found");
      return;
    }
    setProject(p);
    setError(null);
    const [ts, ds, fs, ag, ac] = await Promise.all([
      loadTasks(p.id),
      loadDocuments(p.id),
      loadFiles(p.id),
      loadAgents(),
      loadActivity(p.id),
    ]);
    setTasks(ts);
    setDocs(ds);
    setFiles(fs);
    setAgents(ag);
    setActivity(ac);
  }, [id]);

  useEffect(() => {
    void reload();
  }, [reload, mode]);

  const setTab = (next: Tab, task?: string) => {
    const q = new URLSearchParams();
    q.set("tab", next);
    if (task) q.set("task", task);
    router.replace(`/projects/${id}?${q.toString()}`);
  };

  const grouped = useMemo(() => {
    const map = Object.fromEntries(TASK_COLUMNS.map((c) => [c, [] as OsTask[]])) as Record<OsTaskStatus, OsTask[]>;
    for (const t of tasks) map[t.status].push(t);
    return map;
  }, [tasks]);

  if (!project) {
    return (
      <div className="p-5">
        <Empty title={error ?? "Loading project"} hint="If this persists, create a project from Today." />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-border px-5 py-3">
        <div className="text-[11px] text-muted-foreground">
          <Link href="/projects" className="hover:text-foreground">Projects</Link>
          <span className="mx-1">/</span>
          {project.name}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h1 className="text-[18px] font-semibold">{project.name}</h1>
          <StatusBadge status={project.status} label={PROJECT_STATUS_LABEL[project.status]} />
          <span className="text-[12px] text-muted-foreground">{project.priority}</span>
          <span className="tabular-nums text-[12px] text-muted-foreground">{project.progress}%</span>
          {project.deadline && <span className="text-[12px] text-muted-foreground">due {project.deadline}</span>}
          {project.currentAgentId && <span className="text-[12px]">agent {project.currentAgentId}</span>}
        </div>
        <p className="mt-1 max-w-3xl text-[12px] text-muted-foreground">{project.description || "No description"}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {project.backendProjectId && (
            <Button
              size="sm"
              onClick={() => {
                setFirmwareId(project.backendProjectId!);
                router.push("/workspace");
              }}
            >
              打开 Workspace
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => void patchProject(project.id, { status: project.status === "paused" ? "active" : "paused" }).then(() => reload())}
          >
            {project.status === "paused" ? "Resume" : "Pause"}
          </Button>
        </div>
      </header>

      <nav className="flex gap-1 border-b border-border px-3">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t, selectedTaskId ?? undefined)}
            className={`px-3 py-2 text-[12px] capitalize ${tab === t ? "border-b-2 border-primary text-foreground" : "text-muted-foreground hover:text-foreground"}`}
          >
            {t}
          </button>
        ))}
      </nav>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        {tab === "overview" && (
          <div className="grid gap-3 lg:grid-cols-2">
            <section className="rounded-md border border-border bg-panel p-3">
              <h2 className="text-[12px] font-medium">Next Action</h2>
              <p className="mt-2 text-[13px]">
                {tasks.find((t) => t.status === "review")?.title
                  ?? tasks.find((t) => t.status === "agent_running")?.title
                  ?? tasks.find((t) => t.status === "todo")?.title
                  ?? "Create a task."}
              </p>
            </section>
            <section className="rounded-md border border-border bg-panel p-3">
              <h2 className="text-[12px] font-medium">Recent Activity</h2>
              <ul className="mt-2 space-y-1 text-[12px] text-muted-foreground">
                {activity.slice(0, 8).map((a) => (
                  <li key={a.id}>{a.actorType} {a.verb} {a.objectType}</li>
                ))}
              </ul>
            </section>
          </div>
        )}

        {tab === "tasks" && (
          <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div>
              <form
                className="mb-3 flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!title.trim()) return;
                  void createTask(project.id, { title: title.trim() }).then(() => {
                    setTitle("");
                    void reload();
                  });
                }}
              >
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="New task"
                  className="h-7 flex-1 rounded-sm border border-border bg-background px-2 text-[12px]"
                />
                <Button type="submit">Add task</Button>
              </form>
              <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
                {TASK_COLUMNS.map((col) => (
                  <div key={col} className="rounded-md border border-border bg-panel">
                    <div className="border-b border-border px-2 py-1.5 text-[11px] text-muted-foreground">
                      {TASK_STATUS_LABEL[col]} {grouped[col].length}
                    </div>
                    {grouped[col].map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setTab("tasks", t.id)}
                        className={`block w-full border-t border-border px-2 py-2 text-left text-[12px] hover:bg-accent/40 ${selected?.id === t.id ? "bg-accent" : ""}`}
                      >
                        {t.title}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
            <aside className="rounded-md border border-border bg-panel p-3">
              {selected ? (
                <TaskDetail
                  task={selected}
                  agents={agents}
                  assignError={assignError}
                  events={events}
                  statusText={statusText}
                  activeRunId={activeRun?.id}
                  onPatch={(patch) => void patchTask(selected.id, patch).then(() => reload())}
                  onAssign={async (agentId) => {
                    setAssignError(null);
                    try {
                      const result = await assignTask(selected.id, agentId);
                      const prompt = `${selected.title}\n\n${selected.description}`;
                      setPrompt(prompt);
                      if (project.backendProjectId) setFirmwareId(project.backendProjectId);
                      if (result.runId && result.runId !== "demo-run") {
                        attachRun(result.runId, project.backendProjectId || project.id, prompt);
                      }
                      await reload();
                    } catch (e) {
                      setAssignError(e instanceof OsApiError ? e.reason || e.message : "assign failed");
                    }
                  }}
                  onReview={(d) => void reviewTask(selected.id, d).then(() => reload())}
                />
              ) : (
                <Empty title="Select a task" hint="Assign Agent lives in the task detail." />
              )}
            </aside>
          </div>
        )}

        {tab === "docs" && (
          <div className="max-w-2xl space-y-3">
            <form
              className="space-y-2 rounded-md border border-border bg-panel p-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!docTitle.trim()) return;
                void createDocument(project.id, { title: docTitle.trim(), body: docBody, kind: "note" }).then(() => {
                  setDocTitle("");
                  setDocBody("");
                  void reload();
                });
              }}
            >
              <input value={docTitle} onChange={(e) => setDocTitle(e.target.value)} placeholder="Document title" className="h-7 w-full rounded-sm border border-border bg-background px-2 text-[12px]" />
              <textarea value={docBody} onChange={(e) => setDocBody(e.target.value)} rows={4} className="w-full rounded-sm border border-border bg-background px-2 py-1 text-[12px]" />
              <Button type="submit">Save note</Button>
            </form>
            {docs.map((d) => (
              <article key={d.id} className="rounded-md border border-border bg-panel p-3">
                <div className="text-[13px] font-medium">{d.title}</div>
                <div className="text-[11px] text-muted-foreground">{d.kind}</div>
                <p className="mt-2 whitespace-pre-wrap text-[12px]">{d.body}</p>
              </article>
            ))}
            {docs.length === 0 && <Empty title="No documents" hint="PRD, design notes, and agent output live here." />}
          </div>
        )}

        {tab === "files" && (
          <div className="rounded-md border border-border bg-panel">
            {files.length === 0 ? (
              <div className="p-3"><Empty title="No files" hint="Firmware projects list workspace files when LIVE." /></div>
            ) : (
              files.slice(0, 200).map((f) => (
                <div key={f.path} className="border-t border-border px-3 py-1 font-mono text-[11px]">
                  {f.path}
                </div>
              ))
            )}
          </div>
        )}

        {tab === "agents" && (
          <div className="grid gap-2 md:grid-cols-2">
            {agents.map((a) => (
              <div key={a.id} className="rounded-md border border-border bg-panel p-3">
                <div className="flex items-center justify-between">
                  <div className="text-[13px] font-medium">{a.name}</div>
                  <StatusBadge status={a.status} />
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground">{a.provider} · {a.type}</div>
                <p className="mt-2 text-[12px]">{a.description}</p>
                <div className="mt-2 text-[11px]">{a.runnable ? "Runnable" : "Planned — cannot execute"}</div>
                <div className="mt-1 text-[11px] text-muted-foreground">
                  current tasks: {tasks.filter((t) => t.agentId === a.id && t.status === "agent_running").map((t) => t.title).join(", ") || "—"}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "activity" && (
          <ul className="rounded-md border border-border bg-panel">
            {activity.map((a) => (
              <li key={a.id} className="border-t border-border px-3 py-2 text-[12px]">
                <span className="font-mono text-[11px]">{a.createdAt}</span> · {a.actorType} {a.verb} {a.objectType}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function TaskDetail({
  task,
  agents,
  assignError,
  events,
  statusText,
  activeRunId,
  onPatch,
  onAssign,
  onReview,
}: {
  task: OsTask;
  agents: OsAgent[];
  assignError: string | null;
  events: { id: string; title: string; type: string; status?: string }[];
  statusText: string;
  activeRunId?: string;
  onPatch: (patch: Partial<OsTask>) => void;
  onAssign: (agentId: string) => Promise<void>;
  onReview: (decision: string) => void;
}) {
  const [agentId, setAgentId] = useState("c-agent");
  return (
    <div className="space-y-3">
      <h2 className="text-[13px] font-medium">{task.title}</h2>
      <p className="text-[12px] text-muted-foreground">{task.description || "No description"}</p>
      <div className="flex flex-wrap gap-1">
        <StatusBadge status={task.status} label={TASK_STATUS_LABEL[task.status]} />
        <span className="text-[11px] text-muted-foreground">{task.priority}</span>
        {task.assignee && <span className="text-[11px]">assignee {task.assignee}</span>}
        {task.agentId && <span className="text-[11px]">agent {task.agentId}</span>}
      </div>
      <label className="block text-[11px] text-muted-foreground">Status</label>
      <select
        value={task.status}
        onChange={(e) => onPatch({ status: e.target.value as OsTaskStatus })}
        className="h-7 w-full rounded-sm border border-border bg-background text-[12px]"
      >
        {TASK_COLUMNS.map((s) => (
          <option key={s} value={s}>{TASK_STATUS_LABEL[s]}</option>
        ))}
      </select>

      <div className="border-t border-border pt-3">
        <div className="text-[12px] font-medium">Assign Agent</div>
        <select value={agentId} onChange={(e) => setAgentId(e.target.value)} className="mt-1 h-7 w-full rounded-sm border border-border bg-background text-[12px]">
          {agents.map((a) => (
            <option key={a.id} value={a.id} disabled={!a.runnable}>
              {a.name}{a.runnable ? "" : " (planned)"}
            </option>
          ))}
        </select>
        <Button className="mt-2 w-full" onClick={() => void onAssign(agentId)}>
          Assign Agent
        </Button>
        {assignError && <p className="mt-1 text-[11px] text-error">{assignError}</p>}
      </div>

      {(task.status === "agent_running" || task.runId) && (
        <div className="border-t border-border pt-3">
          <div className="text-[12px] font-medium">Execution</div>
          <div className="mt-1 text-[11px] text-muted-foreground">{statusText}</div>
          <div className="mt-1 font-mono text-[11px]">run {task.runId || activeRunId || "—"}</div>
          <ul className="mt-2 max-h-40 overflow-auto text-[11px]">
            {events.slice(-12).map((e) => (
              <li key={e.id}>{e.type} · {e.title}</li>
            ))}
          </ul>
        </div>
      )}

      {task.status === "review" && (
        <div className="flex flex-wrap gap-1 border-t border-border pt-3">
          <Button size="sm" onClick={() => onReview("approved")}>Approve</Button>
          <Button size="sm" variant="outline" onClick={() => onReview("changes_requested")}>Request changes</Button>
          <Button size="sm" variant="outline" onClick={() => onReview("retry")}>Retry</Button>
          <Button size="sm" variant="destructive" onClick={() => onReview("rejected")}>Reject</Button>
        </div>
      )}
    </div>
  );
}

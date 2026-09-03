from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.runtime import RUNS, AgentRun, run_agent
from app.os_store import (
    RUNNABLE_AGENT_ID,
    add_activity,
    create_document,
    create_os_project,
    create_task,
    get_agent,
    get_os_project,
    get_task,
    list_activity,
    list_agents,
    list_documents,
    list_os_projects,
    list_tasks,
    patch_os_project,
    patch_task,
    set_agent_status,
    set_task_run,
    today_payload,
)
from app.tools.filesystem import list_files
from app.workspace.manager import project_root

router = APIRouter(prefix="/api/os", tags=["os"])


class ProjectBody(BaseModel):
    name: str = "Untitled project"
    description: str = ""
    kind: str = "general"
    status: str = "active"
    priority: str = "medium"
    deadline: str | None = None
    owner: str = "user"
    backendProjectId: str | None = None
    currentAgentId: str | None = None
    workspaceId: str = "default"


class ProjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    deadline: str | None = None
    owner: str | None = None
    backendProjectId: str | None = None
    currentAgentId: str | None = None


class TaskBody(BaseModel):
    title: str = "Untitled task"
    description: str = ""
    status: str = "todo"
    priority: str = "medium"
    dueAt: str | None = None
    assignee: str = "user"
    agentId: str | None = None
    parentId: str | None = None
    labels: list[str] = Field(default_factory=list)


class TaskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    dueAt: str | None = None
    assignee: str | None = None
    agentId: str | None = None
    parentId: str | None = None
    labels: list[str] | None = None
    runId: str | None = None


class AssignBody(BaseModel):
    agentId: str


class ReviewBody(BaseModel):
    decision: str


class DocumentBody(BaseModel):
    title: str = "Untitled"
    kind: str = "note"
    body: str = ""


def _camel_project(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": p["id"],
        "workspaceId": p.get("workspace_id"),
        "backendProjectId": p.get("backend_project_id"),
        "kind": p.get("kind"),
        "name": p.get("name"),
        "description": p.get("description") or "",
        "status": p.get("status"),
        "priority": p.get("priority"),
        "deadline": p.get("deadline"),
        "owner": p.get("owner"),
        "currentAgentId": p.get("current_agent_id"),
        "progress": p.get("progress") or 0,
        "createdAt": p.get("created_at"),
        "updatedAt": p.get("updated_at"),
    }


def _camel_task(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": t["id"],
        "projectId": t.get("project_id"),
        "title": t.get("title"),
        "description": t.get("description") or "",
        "status": t.get("status"),
        "priority": t.get("priority"),
        "dueAt": t.get("due_at"),
        "assignee": t.get("assignee"),
        "agentId": t.get("agent_id"),
        "runId": t.get("run_id"),
        "parentId": t.get("parent_id"),
        "labels": t.get("labels") or [],
        "createdAt": t.get("created_at"),
        "updatedAt": t.get("updated_at"),
    }


def _camel_activity(a: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": a.get("id"),
        "projectId": a.get("project_id") or a.get("projectId"),
        "taskId": a.get("task_id") or a.get("taskId"),
        "agentId": a.get("agent_id") or a.get("agentId"),
        "runId": a.get("run_id") or a.get("runId"),
        "actorType": a.get("actor_type") or a.get("actorType"),
        "verb": a.get("verb"),
        "objectType": a.get("object_type") or a.get("objectType"),
        "objectId": a.get("object_id") or a.get("objectId"),
        "payload": a.get("payload") or {},
        "createdAt": a.get("created_at") or a.get("createdAt"),
    }


def _camel_doc(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": d.get("id"),
        "projectId": d.get("project_id") or d.get("projectId"),
        "title": d.get("title"),
        "kind": d.get("kind"),
        "body": d.get("body") or "",
        "createdAt": d.get("created_at") or d.get("createdAt"),
    }


@router.get("/projects")
def os_projects() -> list[dict[str, Any]]:
    return [_camel_project(p) for p in list_os_projects()]


@router.post("/projects")
def os_projects_create(body: ProjectBody) -> dict[str, Any]:
    return _camel_project(create_os_project(body.model_dump()))


@router.get("/projects/{project_id}")
def os_project_get(project_id: str) -> dict[str, Any]:
    item = get_os_project(project_id)
    if not item:
        raise HTTPException(404, "project not found")
    return _camel_project(item)


@router.patch("/projects/{project_id}")
def os_project_patch(project_id: str, body: ProjectPatch) -> dict[str, Any]:
    item = patch_os_project(project_id, {k: v for k, v in body.model_dump().items() if v is not None})
    if not item:
        raise HTTPException(404, "project not found")
    return _camel_project(item)


@router.get("/projects/{project_id}/tasks")
def os_project_tasks(project_id: str) -> list[dict[str, Any]]:
    if not get_os_project(project_id):
        raise HTTPException(404, "project not found")
    return [_camel_task(t) for t in list_tasks(project_id)]


@router.post("/projects/{project_id}/tasks")
def os_project_task_create(project_id: str, body: TaskBody) -> dict[str, Any]:
    project = get_os_project(project_id)
    if not project:
        raise HTTPException(404, "project not found")
    return _camel_task(create_task(project["id"], body.model_dump()))


@router.get("/tasks/{task_id}")
def os_task_get(task_id: str) -> dict[str, Any]:
    item = get_task(task_id)
    if not item:
        raise HTTPException(404, "task not found")
    return _camel_task(item)


@router.patch("/tasks/{task_id}")
def os_task_patch(task_id: str, body: TaskPatch) -> dict[str, Any]:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    item = patch_task(task_id, data)
    if not item:
        raise HTTPException(404, "task not found")
    return _camel_task(item)


@router.post("/tasks/{task_id}/assign")
async def os_task_assign(task_id: str, body: AssignBody) -> dict[str, Any]:
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    agent = get_agent(body.agentId)
    if not agent:
        raise HTTPException(404, "agent not found")
    if body.agentId != RUNNABLE_AGENT_ID:
        raise HTTPException(
            409,
            {
                "code": "agent_unavailable",
                "reason": f"{agent['name']} is planned and cannot execute in P0. Use C-Agent.",
            },
        )
    project = get_os_project(task["project_id"])
    if not project:
        raise HTTPException(404, "project not found")
    firmware_id = project.get("backend_project_id")
    if not firmware_id:
        raise HTTPException(
            409,
            {
                "code": "no_firmware_workspace",
                "reason": "C-Agent needs a firmware workspace. Link backendProjectId or create an STM32 project.",
            },
        )
    try:
        project_root(firmware_id)
    except FileNotFoundError:
        raise HTTPException(409, {"code": "workspace_missing", "reason": "firmware workspace directory not found"}) from None

    prompt = f"{task['title']}\n\n{task.get('description') or ''}".strip()
    rid = f"run-{uuid.uuid4().hex[:10]}"
    run = AgentRun(rid, firmware_id, prompt, "auto")
    run.task_id = task_id
    run.os_project_id = project["id"]
    RUNS[rid] = run
    set_task_run(task_id, status="agent_running", agent_id=body.agentId, run_id=rid)
    set_agent_status(body.agentId, "running")
    patch_os_project(project["id"], {"currentAgentId": body.agentId, "status": "active"})
    add_activity(
        project_id=project["id"],
        task_id=task_id,
        agent_id=body.agentId,
        run_id=rid,
        actor_type="user",
        verb="assigned",
        object_type="task",
        object_id=task_id,
        payload={"agentId": body.agentId},
    )
    add_activity(
        project_id=project["id"],
        task_id=task_id,
        agent_id=body.agentId,
        run_id=rid,
        actor_type="agent",
        verb="started",
        object_type="run",
        object_id=rid,
        payload={"prompt": prompt[:400]},
    )
    run.task = asyncio.create_task(run_agent(run))
    updated = get_task(task_id)
    assert updated is not None
    return {"task": _camel_task(updated), "runId": rid, "agentId": body.agentId}


@router.post("/tasks/{task_id}/review")
def os_task_review(task_id: str, body: ReviewBody) -> dict[str, Any]:
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    decision = body.decision
    mapping = {
        "approved": "done",
        "changes_requested": "in_progress",
        "retry": "todo",
        "rejected": "blocked",
    }
    if decision not in mapping:
        raise HTTPException(400, "invalid decision")
    item = patch_task(task_id, {"status": mapping[decision]})
    assert item is not None
    add_activity(
        project_id=task["project_id"],
        task_id=task_id,
        actor_type="user",
        verb="reviewed",
        object_type="task",
        object_id=task_id,
        payload={"decision": decision, "status": mapping[decision]},
    )
    if decision == "retry" and task.get("agent_id"):
        return {"task": _camel_task(item), "hint": "reassign"}
    return {"task": _camel_task(item)}


@router.get("/agents")
def os_agents() -> list[dict[str, Any]]:
    return list_agents()


@router.get("/activity")
def os_activity(projectId: str = "", limit: int = 80) -> list[dict[str, Any]]:
    return [_camel_activity(a) for a in list_activity(projectId or None, limit)]


@router.get("/today")
def os_today() -> dict[str, Any]:
    data = today_payload()
    return {
        "myTasks": [_camel_task(t) for t in data["myTasks"]],
        "agentRunning": [_camel_task(t) for t in data["agentRunning"]],
        "needsReview": [_camel_task(t) for t in data["needsReview"]],
        "blocked": [_camel_task(t) for t in data["blocked"]],
        "upcoming": [_camel_task(t) for t in data["upcoming"]],
        "recentActivity": [_camel_activity(a) for a in data["recentActivity"]],
        "blockedProjects": [_camel_project(p) for p in data["blockedProjects"]],
        "focus": _camel_task(data["focus"]) if data["focus"] else None,
        "counts": data["counts"],
    }


@router.get("/projects/{project_id}/documents")
def os_docs(project_id: str) -> list[dict[str, Any]]:
    if not get_os_project(project_id):
        raise HTTPException(404, "project not found")
    return [_camel_doc(d) for d in list_documents(project_id)]


@router.post("/projects/{project_id}/documents")
def os_docs_create(project_id: str, body: DocumentBody) -> dict[str, Any]:
    project = get_os_project(project_id)
    if not project:
        raise HTTPException(404, "project not found")
    return _camel_doc(create_document(project["id"], body.model_dump()))


@router.get("/projects/{project_id}/files")
def os_files(project_id: str) -> list[dict[str, Any]]:
    project = get_os_project(project_id)
    if not project:
        raise HTTPException(404, "project not found")
    firmware = project.get("backend_project_id")
    if not firmware:
        return []
    try:
        names = list_files(project_root(firmware))
    except FileNotFoundError:
        return []
    out = []
    for path in names[:400]:
        lower = path.lower()
        mime = "text/plain"
        if lower.endswith((".c", ".h", ".cpp", ".hpp")):
            mime = "text/x-c"
        elif lower.endswith(".json"):
            mime = "application/json"
        elif lower.endswith(".md"):
            mime = "text/markdown"
        elif lower.endswith((".png", ".jpg")):
            mime = "image"
        elif lower.endswith(".pdf"):
            mime = "application/pdf"
        out.append({"path": path, "source": "workspace", "mime": mime})
    return out

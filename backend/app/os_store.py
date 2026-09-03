from __future__ import annotations

import json
import uuid
from typing import Any

from app.db import connect, now
from app.workspace.manager import list_projects as list_firmware_projects

PROJECT_STATUSES = ("planned", "active", "paused", "completed", "archived")
TASK_STATUSES = ("todo", "in_progress", "agent_running", "review", "blocked", "done")
PRIORITIES = ("low", "medium", "high", "urgent")
DOC_KINDS = ("prd", "design", "note", "agent_output")
RUNNABLE_AGENT_ID = "c-agent"

SEED_AGENTS: list[dict[str, Any]] = [
    {
        "id": "c-agent",
        "name": "C-Agent",
        "provider": "local-runtime",
        "model": "configured-llm",
        "type": "embedded",
        "description": "STM32F103 HAL firmware agent with compile / flash / serial tools.",
        "capabilities": ["code", "compile", "flash", "serial", "review"],
        "status": "idle",
        "endpoint": "",
        "config": {},
    },
    {
        "id": "codex",
        "name": "Codex",
        "provider": "openai",
        "model": "",
        "type": "coding",
        "description": "Planned coding agent. Not wired in P0.",
        "capabilities": ["code"],
        "status": "planned",
        "endpoint": "",
        "config": {},
    },
    {
        "id": "claude-code",
        "name": "Claude Code",
        "provider": "anthropic",
        "model": "",
        "type": "coding",
        "description": "Planned coding agent. Not wired in P0.",
        "capabilities": ["code"],
        "status": "planned",
        "endpoint": "",
        "config": {},
    },
    {
        "id": "grok",
        "name": "Grok",
        "provider": "xai",
        "model": "",
        "type": "general",
        "description": "Planned general agent. Not wired in P0.",
        "capabilities": ["general"],
        "status": "planned",
        "endpoint": "",
        "config": {},
    },
    {
        "id": "custom",
        "name": "Custom Agent",
        "provider": "custom",
        "model": "",
        "type": "general",
        "description": "User-defined agent slot. Not wired in P0.",
        "capabilities": [],
        "status": "planned",
        "endpoint": "",
        "config": {},
    },
]


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _row(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def seed_agents() -> None:
    with connect() as con:
        for agent in SEED_AGENTS:
            con.execute(
                """INSERT INTO agents(id, name, provider, model, type, description, capabilities_json, status, endpoint, config_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     name=excluded.name,
                     provider=excluded.provider,
                     type=excluded.type,
                     description=excluded.description,
                     capabilities_json=excluded.capabilities_json,
                     status=CASE WHEN agents.status IN ('running','waiting','error') THEN agents.status ELSE excluded.status END""",
                (
                    agent["id"],
                    agent["name"],
                    agent["provider"],
                    agent["model"],
                    agent["type"],
                    agent["description"],
                    json.dumps(agent["capabilities"]),
                    agent["status"],
                    agent["endpoint"],
                    json.dumps(agent["config"]),
                ),
            )


def sync_firmware_projects() -> None:
    stamp = now()
    try:
        items = list_firmware_projects()
    except OSError:
        return
    with connect() as con:
        for meta in items:
            fid = str(meta.get("id") or "")
            if not fid:
                continue
            existing = con.execute(
                "SELECT id FROM os_projects WHERE backend_project_id=?",
                (fid,),
            ).fetchone()
            if existing:
                con.execute(
                    "UPDATE os_projects SET name=?, updated_at=? WHERE id=?",
                    (meta.get("name") or fid, stamp, existing["id"]),
                )
                continue
            con.execute(
                """INSERT INTO os_projects(
                     id, workspace_id, backend_project_id, kind, name, description, status, priority,
                     deadline, owner, current_agent_id, progress, created_at, updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    _id("osp"),
                    "default",
                    fid,
                    "firmware",
                    meta.get("name") or fid,
                    meta.get("board") or meta.get("mcu") or "",
                    "active",
                    "medium",
                    None,
                    "user",
                    "c-agent",
                    0,
                    stamp,
                    stamp,
                ),
            )


def list_agents() -> list[dict[str, Any]]:
    seed_agents()
    with connect() as con:
        rows = con.execute(
            "SELECT id, name, provider, model, type, description, capabilities_json, status, endpoint FROM agents ORDER BY name"
        ).fetchall()
    out = []
    for r in rows:
        item = _row(r)
        try:
            item["capabilities"] = json.loads(item.pop("capabilities_json") or "[]")
        except json.JSONDecodeError:
            item["capabilities"] = []
        item["runnable"] = item["id"] == RUNNABLE_AGENT_ID
        out.append(item)
    return out


def get_agent(agent_id: str) -> dict[str, Any] | None:
    seed_agents()
    with connect() as con:
        row = con.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
    if not row:
        return None
    item = _row(row)
    try:
        item["capabilities"] = json.loads(item.pop("capabilities_json") or "[]")
    except json.JSONDecodeError:
        item["capabilities"] = []
    item.pop("config_json", None)
    item["runnable"] = item["id"] == RUNNABLE_AGENT_ID
    return item


def set_agent_status(agent_id: str, status: str) -> None:
    with connect() as con:
        con.execute("UPDATE agents SET status=? WHERE id=?", (status, agent_id))


def _project_progress(con: Any, project_id: str) -> int:
    total = con.execute("SELECT COUNT(*) AS n FROM tasks WHERE project_id=?", (project_id,)).fetchone()["n"]
    if not total:
        return 0
    done = con.execute(
        "SELECT COUNT(*) AS n FROM tasks WHERE project_id=? AND status=?",
        (project_id, "done"),
    ).fetchone()["n"]
    return int(round(100 * done / total))


def refresh_progress(project_id: str) -> int:
    with connect() as con:
        progress = _project_progress(con, project_id)
        con.execute(
            "UPDATE os_projects SET progress=?, updated_at=? WHERE id=?",
            (progress, now(), project_id),
        )
    return progress


def serialize_project(row: Any) -> dict[str, Any]:
    item = _row(row)
    return item


def list_os_projects() -> list[dict[str, Any]]:
    seed_agents()
    sync_firmware_projects()
    with connect() as con:
        rows = con.execute("SELECT * FROM os_projects ORDER BY updated_at DESC").fetchall()
    return [serialize_project(r) for r in rows]


def get_os_project(project_id: str) -> dict[str, Any] | None:
    seed_agents()
    sync_firmware_projects()
    with connect() as con:
        row = con.execute("SELECT * FROM os_projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            row = con.execute("SELECT * FROM os_projects WHERE backend_project_id=?", (project_id,)).fetchone()
    return serialize_project(row) if row else None


def create_os_project(body: dict[str, Any]) -> dict[str, Any]:
    seed_agents()
    stamp = now()
    pid = _id("osp")
    kind = body.get("kind") if body.get("kind") in {"firmware", "general"} else "general"
    status = body.get("status") if body.get("status") in PROJECT_STATUSES else "active"
    priority = body.get("priority") if body.get("priority") in PRIORITIES else "medium"
    with connect() as con:
        con.execute(
            """INSERT INTO os_projects(
                 id, workspace_id, backend_project_id, kind, name, description, status, priority,
                 deadline, owner, current_agent_id, progress, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pid,
                body.get("workspaceId") or "default",
                body.get("backendProjectId"),
                kind,
                str(body.get("name") or "Untitled project"),
                str(body.get("description") or ""),
                status,
                priority,
                body.get("deadline"),
                body.get("owner") or "user",
                body.get("currentAgentId"),
                0,
                stamp,
                stamp,
            ),
        )
    add_activity(
        project_id=pid,
        actor_type="user",
        verb="created",
        object_type="project",
        object_id=pid,
        payload={"name": body.get("name")},
    )
    item = get_os_project(pid)
    assert item is not None
    return item


def patch_os_project(project_id: str, body: dict[str, Any]) -> dict[str, Any] | None:
    current = get_os_project(project_id)
    if not current:
        return None
    fields = {
        "name": body.get("name", current["name"]),
        "description": body.get("description", current["description"]),
        "status": body["status"] if body.get("status") in PROJECT_STATUSES else current["status"],
        "priority": body["priority"] if body.get("priority") in PRIORITIES else current["priority"],
        "deadline": body.get("deadline", current["deadline"]),
        "owner": body.get("owner", current["owner"]),
        "current_agent_id": body.get("currentAgentId", current["current_agent_id"]),
        "backend_project_id": body.get("backendProjectId", current["backend_project_id"]),
    }
    with connect() as con:
        con.execute(
            """UPDATE os_projects SET name=?, description=?, status=?, priority=?, deadline=?, owner=?,
               current_agent_id=?, backend_project_id=?, updated_at=? WHERE id=?""",
            (
                fields["name"],
                fields["description"],
                fields["status"],
                fields["priority"],
                fields["deadline"],
                fields["owner"],
                fields["current_agent_id"],
                fields["backend_project_id"],
                now(),
                current["id"],
            ),
        )
    add_activity(
        project_id=current["id"],
        actor_type="user",
        verb="updated",
        object_type="project",
        object_id=current["id"],
        payload={"fields": list(body.keys())},
    )
    return get_os_project(current["id"])


def serialize_task(row: Any) -> dict[str, Any]:
    item = _row(row)
    try:
        item["labels"] = json.loads(item.pop("labels_json") or "[]")
    except json.JSONDecodeError:
        item["labels"] = []
        item.pop("labels_json", None)
    return item


def list_tasks(project_id: str | None = None) -> list[dict[str, Any]]:
    with connect() as con:
        if project_id:
            rows = con.execute(
                "SELECT * FROM tasks WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM tasks ORDER BY updated_at DESC").fetchall()
    return [serialize_task(r) for r in rows]


def get_task(task_id: str) -> dict[str, Any] | None:
    with connect() as con:
        row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return serialize_task(row) if row else None


def create_task(project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    stamp = now()
    tid = _id("tsk")
    status = body.get("status") if body.get("status") in TASK_STATUSES else "todo"
    priority = body.get("priority") if body.get("priority") in PRIORITIES else "medium"
    labels = body.get("labels") if isinstance(body.get("labels"), list) else []
    with connect() as con:
        con.execute(
            """INSERT INTO tasks(
                 id, project_id, title, description, status, priority, due_at, assignee, agent_id,
                 run_id, parent_id, labels_json, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tid,
                project_id,
                str(body.get("title") or "Untitled task"),
                str(body.get("description") or ""),
                status,
                priority,
                body.get("dueAt"),
                body.get("assignee") or "user",
                body.get("agentId"),
                None,
                body.get("parentId"),
                json.dumps(labels),
                stamp,
                stamp,
            ),
        )
    refresh_progress(project_id)
    add_activity(
        project_id=project_id,
        task_id=tid,
        actor_type="user",
        verb="created",
        object_type="task",
        object_id=tid,
        payload={"title": body.get("title")},
    )
    item = get_task(tid)
    assert item is not None
    return item


def patch_task(task_id: str, body: dict[str, Any]) -> dict[str, Any] | None:
    current = get_task(task_id)
    if not current:
        return None
    labels = body.get("labels") if isinstance(body.get("labels"), list) else current.get("labels") or []
    with connect() as con:
        con.execute(
            """UPDATE tasks SET title=?, description=?, status=?, priority=?, due_at=?, assignee=?,
               agent_id=?, run_id=?, parent_id=?, labels_json=?, updated_at=? WHERE id=?""",
            (
                body.get("title", current["title"]),
                body.get("description", current["description"]),
                body["status"] if body.get("status") in TASK_STATUSES else current["status"],
                body["priority"] if body.get("priority") in PRIORITIES else current["priority"],
                body.get("dueAt", current["due_at"]),
                body.get("assignee", current["assignee"]),
                body.get("agentId", current["agent_id"]),
                body.get("runId", current["run_id"]),
                body.get("parentId", current["parent_id"]),
                json.dumps(labels),
                now(),
                task_id,
            ),
        )
    refresh_progress(current["project_id"])
    if body.get("status") and body["status"] != current["status"]:
        add_activity(
            project_id=current["project_id"],
            task_id=task_id,
            actor_type="user",
            verb="status_changed",
            object_type="task",
            object_id=task_id,
            payload={"from": current["status"], "to": body["status"]},
        )
    return get_task(task_id)


def set_task_run(task_id: str, *, status: str, agent_id: str | None, run_id: str | None) -> None:
    with connect() as con:
        con.execute(
            "UPDATE tasks SET status=?, agent_id=?, run_id=?, updated_at=? WHERE id=?",
            (status, agent_id, run_id, now(), task_id),
        )
    task = get_task(task_id)
    if task:
        refresh_progress(task["project_id"])


def add_activity(
    *,
    project_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    actor_type: str,
    verb: str,
    object_type: str,
    object_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    aid = _id("act")
    stamp = now()
    with connect() as con:
        con.execute(
            """INSERT INTO activities(
                 id, project_id, task_id, agent_id, run_id, actor_type, verb, object_type, object_id, payload_json, created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                aid,
                project_id,
                task_id,
                agent_id,
                run_id,
                actor_type,
                verb,
                object_type,
                object_id,
                json.dumps(payload or {}, ensure_ascii=False),
                stamp,
            ),
        )
    return {
        "id": aid,
        "projectId": project_id,
        "taskId": task_id,
        "agentId": agent_id,
        "runId": run_id,
        "actorType": actor_type,
        "verb": verb,
        "objectType": object_type,
        "objectId": object_id,
        "payload": payload or {},
        "createdAt": stamp,
    }


def list_activity(project_id: str | None = None, limit: int = 80) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 200))
    with connect() as con:
        if project_id:
            rows = con.execute(
                "SELECT * FROM activities WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, cap),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM activities ORDER BY created_at DESC LIMIT ?",
                (cap,),
            ).fetchall()
    out = []
    for r in rows:
        item = _row(r)
        try:
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            item["payload"] = {}
            item.pop("payload_json", None)
        out.append(item)
    return out


def create_document(project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    did = _id("doc")
    kind = body.get("kind") if body.get("kind") in DOC_KINDS else "note"
    stamp = now()
    with connect() as con:
        con.execute(
            "INSERT INTO documents(id, project_id, title, kind, body, created_at) VALUES(?,?,?,?,?,?)",
            (did, project_id, str(body.get("title") or "Untitled"), kind, str(body.get("body") or ""), stamp),
        )
    add_activity(
        project_id=project_id,
        actor_type="user",
        verb="created",
        object_type="document",
        object_id=did,
        payload={"title": body.get("title"), "kind": kind},
    )
    return {"id": did, "projectId": project_id, "title": body.get("title") or "Untitled", "kind": kind, "body": body.get("body") or "", "createdAt": stamp}


def list_documents(project_id: str) -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return [_row(r) for r in rows]


def today_payload() -> dict[str, Any]:
    seed_agents()
    sync_firmware_projects()
    tasks = list_tasks()
    activities = list_activity(limit=20)
    projects = list_os_projects()
    my_tasks = [t for t in tasks if t["status"] in {"todo", "in_progress"}]
    running = [t for t in tasks if t["status"] == "agent_running"]
    review = [t for t in tasks if t["status"] == "review"]
    blocked = [t for t in tasks if t["status"] == "blocked"]
    upcoming = [t for t in tasks if t.get("due_at") and t["status"] not in {"done"}][:8]
    blocked_projects = [p for p in projects if p["status"] == "paused"]
    focus = review[:1] or blocked[:1] or running[:1] or my_tasks[:1]
    return {
        "myTasks": my_tasks[:12],
        "agentRunning": running[:12],
        "needsReview": review[:12],
        "blocked": blocked[:12],
        "upcoming": upcoming,
        "recentActivity": activities,
        "blockedProjects": blocked_projects,
        "focus": focus[0] if focus else None,
        "counts": {
            "attention": len(review) + len(blocked) + len(my_tasks),
            "running": len(running),
            "review": len(review),
            "blocked": len(blocked),
        },
    }

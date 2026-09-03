from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app
from app.workspace.manager import create_project


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    return TestClient(app)


def test_os_project_task_activity_today(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    created = client.post("/api/os/projects", json={"name": "Alpha", "description": "OS project"}).json()
    assert created["name"] == "Alpha"
    assert created["status"] == "active"
    pid = created["id"]

    listed = client.get("/api/os/projects").json()
    assert any(p["id"] == pid for p in listed)

    task = client.post(f"/api/os/projects/{pid}/tasks", json={"title": "Write PRD", "priority": "high"}).json()
    assert task["status"] == "todo"
    tid = task["id"]

    patched = client.patch(f"/api/os/tasks/{tid}", json={"status": "in_progress"}).json()
    assert patched["status"] == "in_progress"

    doc = client.post(f"/api/os/projects/{pid}/documents", json={"title": "PRD", "kind": "prd", "body": "goals"}).json()
    assert doc["kind"] == "prd"

    acts = client.get(f"/api/os/activity?projectId={pid}").json()
    verbs = {a["verb"] for a in acts}
    assert "created" in verbs
    assert "status_changed" in verbs
    assert all("verb" in a and "actorType" in a for a in acts)

    today = client.get("/api/os/today").json()
    assert "myTasks" in today
    assert "counts" in today
    assert any(t["id"] == tid for t in today["myTasks"])


def test_assign_rejects_planned_agent(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    pid = client.post("/api/os/projects", json={"name": "Beta"}).json()["id"]
    tid = client.post(f"/api/os/projects/{pid}/tasks", json={"title": "Fix bug"}).json()["id"]
    res = client.post(f"/api/os/tasks/{tid}/assign", json={"agentId": "codex"})
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "agent_unavailable"


def test_assign_c_agent_requires_firmware(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    pid = client.post("/api/os/projects", json={"name": "Gamma", "kind": "general"}).json()["id"]
    tid = client.post(f"/api/os/projects/{pid}/tasks", json={"title": "Blink LED"}).json()["id"]
    res = client.post(f"/api/os/tasks/{tid}/assign", json={"agentId": "c-agent"})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "no_firmware_workspace"


def test_assign_c_agent_starts_run(tmp_path, monkeypatch):
    async def fake_run(run):
        run.status = "success"
        from app.agent.runtime import _sync_os_task
        from app.db import finish_run

        finish_run(run.id, "success")
        _sync_os_task(run)

    monkeypatch.setattr("app.os_api.run_agent", fake_run)
    client = _client(tmp_path, monkeypatch)
    meta = create_project("LED", "STM32F103C8T6", "HAL")
    pid = client.post(
        "/api/os/projects",
        json={"name": "Firmware", "kind": "firmware", "backendProjectId": meta["id"]},
    ).json()["id"]
    tid = client.post(f"/api/os/projects/{pid}/tasks", json={"title": "Blink PC13"}).json()["id"]
    res = client.post(f"/api/os/tasks/{tid}/assign", json={"agentId": "c-agent"})
    assert res.status_code == 200
    body = res.json()
    assert body["agentId"] == "c-agent"
    assert body["runId"]
    task = client.get(f"/api/os/tasks/{tid}").json()
    assert task["status"] in {"agent_running", "review"}
    assert task["runId"] == body["runId"]


def test_review_approve_done(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    pid = client.post("/api/os/projects", json={"name": "Delta"}).json()["id"]
    tid = client.post(f"/api/os/projects/{pid}/tasks", json={"title": "Review me", "status": "review"}).json()["id"]
    res = client.post(f"/api/os/tasks/{tid}/review", json={"decision": "approved"})
    assert res.status_code == 200
    assert res.json()["task"]["status"] == "done"
    project = client.get(f"/api/os/projects/{pid}").json()
    assert project["progress"] == 100


def test_agents_registry_only_c_agent_runnable(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    agents = client.get("/api/os/agents").json()
    ids = {a["id"] for a in agents}
    assert "c-agent" in ids
    assert "codex" in ids
    c_agent = next(a for a in agents if a["id"] == "c-agent")
    assert c_agent["runnable"] is True
    planned = next(a for a in agents if a["id"] == "codex")
    assert planned["runnable"] is False
    assert planned["status"] == "planned"

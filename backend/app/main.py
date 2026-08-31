from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.runtime import RUNS, AgentRun, event_stream, run_agent
from app.tools.compiler import CompileError, compile_project
from app.tools.detect import gcc_installed, tool_status
from app.tools.filesystem import list_files, read_file, write_file
from app.tools.knowledge import retrieve_knowledge
from app.workspace.manager import create_project, list_projects, project_root
from app.workspace.paths import PathEscapeError

app = FastAPI(title="C-Embedded Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateRunBody(BaseModel):
    prompt: str
    project_id: str = Field(alias="projectId", default="default")
    mode: str = "auto"
    goldenPath: bool = False

    model_config = {"populate_by_name": True}


class CreateProjectBody(BaseModel):
    name: str = "STM32 LED"
    mcu: str = "STM32F103C8T6"
    framework: str = "HAL"


class WriteFileBody(BaseModel):
    path: str
    content: str


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "gcc": "installed" if gcc_installed() else "missing"}


@app.get("/api/knowledge")
def knowledge(q: str = "GPIO PA5") -> list[dict[str, str]]:
    return retrieve_knowledge(q)


@app.get("/api/tools/status")
def tools() -> list[dict[str, Any]]:
    return tool_status()


@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    return list_projects()


@app.post("/api/projects")
def new_project(body: CreateProjectBody) -> dict[str, Any]:
    return create_project(body.name, body.mcu, body.framework)


@app.get("/api/projects/{project_id}/files")
def files(project_id: str) -> list[str]:
    try:
        return list_files(project_root(project_id))
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None


@app.get("/api/projects/{project_id}/file")
def file_get(project_id: str, path: str) -> dict[str, str]:
    try:
        return {"path": path, "content": read_file(project_root(project_id), path)}
    except (FileNotFoundError, PathEscapeError) as e:
        raise HTTPException(400, str(e)) from None


@app.put("/api/projects/{project_id}/file")
def file_put(project_id: str, body: WriteFileBody) -> dict[str, str]:
    try:
        write_file(project_root(project_id), body.path, body.content)
        return {"ok": "1", "path": body.path}
    except (FileNotFoundError, PathEscapeError) as e:
        raise HTTPException(400, str(e)) from None


@app.post("/api/projects/{project_id}/build")
def build(project_id: str) -> dict[str, Any]:
    try:
        return compile_project(project_root(project_id))
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    except CompileError as e:
        return {"success": False, "error": str(e), "diagnostics": [], "artifacts": []}


@app.post("/api/runs")
async def create_run(body: CreateRunBody) -> dict[str, str]:
    rid = f"run-{uuid.uuid4().hex[:10]}"
    run = AgentRun(rid, body.project_id, body.prompt, body.mode)
    RUNS[rid] = run
    asyncio.create_task(run_agent(run))
    return {"id": rid, "run_id": rid}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return {"id": run.id, "status": run.status, "prompt": run.prompt, "events": run.events}


@app.get("/api/runs/{run_id}/events")
async def sse(run_id: str) -> StreamingResponse:
    if run_id not in RUNS:
        raise HTTPException(404, "run not found")
    return StreamingResponse(event_stream(run_id), media_type="text/event-stream")


@app.post("/api/runs/{run_id}/stop")
async def stop(run_id: str) -> dict[str, str]:
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    run.status = "cancelled"
    run.queue.put_nowait(None)
    return {"ok": "1"}


@app.post("/api/runs/{run_id}/approve")
async def approve(run_id: str) -> dict[str, str]:
    if run_id not in RUNS:
        raise HTTPException(404, "run not found")
    return {"ok": "1"}


@app.post("/api/agent/runs")
async def create_run_alias(body: CreateRunBody) -> dict[str, str]:
    return await create_run(body)

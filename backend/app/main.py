from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.agent.runtime import RUNS, AgentRun, event_stream, request_stop, run_agent
from app.config.settings import settings
from app.db import load_run
from app.tools.compiler import CompileError, compile_project
from app.tools.detect import gcc_installed, tool_status
from app.tools.filesystem import list_files, read_file, write_file
from app.tools.flash import FlashError, flash_elf
from app.tools.gitutil import restore_snapshot
from app.tools.knowledge import ingest_pdf, retrieve_knowledge
from app.tools.serialutil import connect as serial_connect
from app.tools.serialutil import disconnect as serial_disconnect
from app.tools.serialutil import list_ports, read_available, status as serial_status
from app.workspace.manager import create_project, list_projects, project_root
from app.workspace.paths import PathEscapeError, ProtectedPathError

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


class IngestBody(BaseModel):
    path: str
    source: str = "RM0008"
    mcu: str = "STM32F103"


class SerialBody(BaseModel):
    device: str
    baud: int = 115200


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "gcc": "installed" if gcc_installed() else "missing"}


@app.get("/api/metrics")
def metrics() -> dict[str, Any]:
    path = settings.repo_root / "benchmarks" / "stm32f103" / "results.json"
    if not path.is_file():
        return {"gcc": gcc_installed(), "skipped": ["no results.json — run python benchmarks/benchmark.py"]}
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/knowledge")
def knowledge(q: str = "GPIO PC13") -> list[dict[str, str]]:
    return retrieve_knowledge(q)


@app.post("/api/knowledge/ingest")
def knowledge_ingest(body: IngestBody) -> dict[str, Any]:
    p = Path(body.path)
    if not p.is_file():
        raise HTTPException(400, "pdf not found")
    n = ingest_pdf(p, source=body.source, mcu=body.mcu)
    return {"pages": n}


@app.get("/api/tools/status")
def tools() -> list[dict[str, Any]]:
    return tool_status()


@app.get("/api/serial/ports")
def serial_ports() -> list[dict[str, Any]]:
    return list_ports()


@app.get("/api/serial/status")
def serial_status_api() -> dict[str, Any]:
    return serial_status()


@app.post("/api/serial/connect")
def serial_connect_api(body: SerialBody) -> dict[str, Any]:
    try:
        return serial_connect(body.device, body.baud)
    except (ValueError, RuntimeError, OSError) as e:
        raise HTTPException(400, str(e)) from None


@app.post("/api/serial/disconnect")
def serial_disconnect_api() -> dict[str, str]:
    return serial_disconnect()


@app.get("/api/serial/lines")
def serial_lines() -> list[dict[str, str]]:
    return read_available()


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
        write_file(project_root(project_id), body.path, body.content, advanced=True)
        return {"ok": "1", "path": body.path}
    except (FileNotFoundError, PathEscapeError, ProtectedPathError) as e:
        raise HTTPException(400, str(e)) from None


@app.post("/api/projects/{project_id}/build")
def build(project_id: str) -> dict[str, Any]:
    try:
        return compile_project(project_root(project_id))
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    except CompileError as e:
        return {"success": False, "error": str(e), "diagnostics": [], "artifacts": []}


@app.get("/api/projects/{project_id}/artifacts")
def artifacts(project_id: str) -> list[dict[str, Any]]:
    try:
        root = project_root(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    out = []
    for name in ("firmware.elf", "firmware.hex", "firmware.bin", "firmware.map"):
        p = root / name
        if p.is_file():
            out.append({"name": name, "size": p.stat().st_size})
    return out


@app.get("/api/projects/{project_id}/artifacts/{name}")
def artifact_download(project_id: str, name: str) -> FileResponse:
    if name not in {"firmware.elf", "firmware.hex", "firmware.bin", "firmware.map"}:
        raise HTTPException(400, "invalid artifact")
    try:
        root = project_root(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    path = root / name
    if not path.is_file():
        raise HTTPException(404, "artifact not found")
    return FileResponse(path, filename=name)


@app.post("/api/projects/{project_id}/flash")
def flash(project_id: str) -> dict[str, Any]:
    try:
        return flash_elf(project_root(project_id))
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    except FlashError as e:
        raise HTTPException(400, str(e)) from None


@app.post("/api/runs")
async def create_run(body: CreateRunBody) -> dict[str, str]:
    rid = f"run-{uuid.uuid4().hex[:10]}"
    run = AgentRun(rid, body.project_id, body.prompt, body.mode)
    RUNS[rid] = run
    run.task = asyncio.create_task(run_agent(run))
    return {"id": rid, "run_id": rid}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run = RUNS.get(run_id)
    if run:
        return {"id": run.id, "status": run.status, "prompt": run.prompt, "events": run.events, "snapshot": run.snapshot_sha}
    stored = load_run(run_id)
    if not stored:
        raise HTTPException(404, "run not found")
    return stored


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
    await request_stop(run)
    return {"ok": "1"}


@app.post("/api/runs/{run_id}/undo")
def undo(run_id: str) -> dict[str, str]:
    run = RUNS.get(run_id)
    if not run or not run.snapshot_sha:
        raise HTTPException(404, "snapshot not found")
    ok = restore_snapshot(project_root(run.project_id), run.snapshot_sha)
    if not ok:
        raise HTTPException(400, "restore failed")
    return {"ok": "1"}


@app.post("/api/runs/{run_id}/approve")
async def approve(run_id: str) -> dict[str, str]:
    if run_id not in RUNS:
        raise HTTPException(404, "run not found")
    return {"ok": "1"}


@app.post("/api/agent/runs")
async def create_run_alias(body: CreateRunBody) -> dict[str, str]:
    return await create_run(body)

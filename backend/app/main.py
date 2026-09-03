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

from app.agent.runtime import RUNS, AgentRun, event_stream, request_stop, resolve_approval, run_agent
from app.config.settings import settings
from app.db import list_runs, load_run
from app.tools.compiler import CompileError, compile_project
from app.tools.detect import connected_devices, environment_status, gcc_installed, tool_status
from app.tools.error_memory import get_error, list_errors, record_from_output
from app.tools.filesystem import list_files, read_file, write_file
from app.tools.flash import FlashError, flash_elf
from app.tools.gitutil import restore_snapshot
from app.tools.hardware_run import auto_debug, run_pipeline
from app.tools.ioc import parse_ioc
from app.tools.knowledge import ingest_pdf, retrieve_knowledge
from app.tools.serialutil import connect as serial_connect
from app.tools.serialutil import disconnect as serial_disconnect
from app.tools.serialutil import list_ports, read_available, status as serial_status
from app.tools.skills import benchmark_wrap, get_skill, list_skills
from app.tools.hw_session import load_session, save_session
from app.tools.project_scan import import_existing_project, scan_existing_project
from app.validation import validate_project
from app.workspace.manager import create_project, list_projects, project_root
from app.workspace.paths import PathEscapeError, ProtectedPathError
from app.os_api import router as os_router

app = FastAPI(title="C-Embedded Agent API")
app.include_router(os_router)
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
    serialDevice: str | None = None
    baud: int = 115200
    expect: str | None = None

    model_config = {"populate_by_name": True}


class ApproveBody(BaseModel):
    approvalId: str | None = None
    decision: str = "approved"


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


class IocBody(BaseModel):
    content: str
    filename: str = "project.ioc"
    name: str | None = None


class HardwareRunBody(BaseModel):
    projectId: str = "default"
    serialDevice: str | None = None
    baud: int = 115200
    expect: str | None = None
    task: str = ""


class ImportExistingBody(BaseModel):
    path: str
    name: str | None = None


class HardwareSessionBody(BaseModel):
    projectId: str
    debugger: str | None = None
    serialDevice: str | None = None
    baud: int | None = None
    board: str | None = None
    mcu: str | None = None


def _version_payload() -> dict[str, Any]:
    root = settings.repo_root
    app_ver = "0.8.0-beta"
    vf = root / "VERSION"
    if vf.is_file():
        app_ver = vf.read_text(encoding="utf-8").strip() or app_ver
    cube = None
    lock = root / "vendor.lock.json"
    if lock.is_file():
        try:
            cube = json.loads(lock.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cube = None
    return {
        "appVersion": app_ver,
        "agentRuntimeVersion": "0.8.0-beta",
        "templateVersion": "stm32f103_hal_official",
        "stm32cubef1Version": (cube or {}).get("STM32CubeF1") or (cube or {}).get("hal") or "STM32CubeF1 in-tree",
        "vendor": cube,
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "gcc": "installed" if gcc_installed() else "missing"}


@app.get("/api/version")
def version() -> dict[str, Any]:
    return _version_payload()


@app.get("/api/metrics")
def metrics() -> dict[str, Any]:
    path = settings.repo_root / "benchmarks" / "stm32f103" / "results.json"
    if not path.is_file():
        return {"gcc": gcc_installed(), "skipped": ["no results.json — run python benchmarks/benchmark.py"]}
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/benchmark")
def benchmark() -> dict[str, Any]:
    return benchmark_wrap(metrics())


@app.get("/api/skills")
def skills() -> list[dict[str, Any]]:
    return list_skills()


@app.get("/api/skills/{skill_id}")
def skill_get(skill_id: str) -> dict[str, Any]:
    item = get_skill(skill_id)
    if not item:
        raise HTTPException(404, "skill not found")
    return item


@app.get("/api/memory/errors")
def memory_errors(q: str = "", tag: str = "") -> list[dict[str, Any]]:
    return list_errors(q, tag)


@app.get("/api/memory/errors/{eid}")
def memory_error(eid: str) -> dict[str, Any]:
    item = get_error(eid)
    if not item:
        raise HTTPException(404, "error memory not found")
    return item


@app.post("/api/projects/analyze-ioc")
def analyze_ioc(body: IocBody) -> dict[str, Any]:
    analysis = parse_ioc(body.content, body.filename)
    return {"available": True, "analysis": analysis}


@app.post("/api/projects/import-ioc")
def import_ioc(body: IocBody) -> dict[str, Any]:
    analysis = parse_ioc(body.content, body.filename)
    name = body.name or Path(body.filename).stem or "CubeMX"
    meta = create_project(name, analysis.get("mcu") or "STM32F103C8T6", "HAL")
    root = project_root(meta["id"])
    (root / body.filename).write_text(body.content, encoding="utf-8")
    (root / "ioc-analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    meta["ioc"] = body.filename
    meta["board"] = analysis.get("board") or meta.get("board")
    (root / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"available": True, "projectId": meta["id"], "analysis": analysis}


@app.get("/api/projects/{project_id}/ioc")
def project_ioc(project_id: str) -> dict[str, Any]:
    try:
        root = project_root(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    cached = root / "ioc-analysis.json"
    if cached.is_file():
        return json.loads(cached.read_text(encoding="utf-8"))
    iocs = list(root.glob("*.ioc"))
    if not iocs:
        raise HTTPException(404, "ioc not found")
    return parse_ioc(iocs[0].read_text(encoding="utf-8"), iocs[0].name)


@app.post("/api/hardware/run")
def hardware_run(body: HardwareRunBody) -> dict[str, Any]:
    try:
        root = project_root(body.projectId)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    return run_pipeline(root, serial_device=body.serialDevice, baud=body.baud, expect=body.expect, task=body.task)


@app.post("/api/hardware/auto-debug")
def hardware_auto_debug(body: HardwareRunBody) -> dict[str, Any]:
    try:
        root = project_root(body.projectId)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    return auto_debug(root, serial_device=body.serialDevice, baud=body.baud, expect=body.expect)


@app.get("/api/validation")
def validation_get(projectId: str = "", prompt: str = "") -> dict[str, Any]:
    if not projectId:
        return {"available": True, "reason": "pass projectId", "passed": False, "score": 0, "checks": {}, "missing": []}
    try:
        root = project_root(projectId)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    return validate_project(root, prompt)


@app.post("/api/projects/scan-existing")
def scan_existing(body: ImportExistingBody) -> dict[str, Any]:
    return scan_existing_project(Path(body.path))


@app.post("/api/projects/import-existing")
def import_existing(body: ImportExistingBody) -> dict[str, Any]:
    src = Path(body.path)
    if not src.is_dir():
        raise HTTPException(400, "path is not a directory")
    return import_existing_project(src, body.name)


@app.get("/api/projects/{project_id}/hardware-session")
def hardware_session_get(project_id: str) -> dict[str, Any]:
    try:
        root = project_root(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    return load_session(root)


@app.post("/api/projects/{project_id}/hardware-session")
def hardware_session_set(project_id: str, body: HardwareSessionBody) -> dict[str, Any]:
    try:
        root = project_root(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    return save_session(
        root,
        debugger=body.debugger,
        serialDevice=body.serialDevice,
        baud=body.baud,
        board=body.board,
        mcu=body.mcu,
    )


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


@app.get("/api/environment")
def environment() -> dict[str, Any]:
    return environment_status()


@app.get("/api/devices")
def devices() -> dict[str, Any]:
    return connected_devices()


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
        result = compile_project(project_root(project_id))
        record_from_output(str(result.get("combined") or ""), success=bool(result.get("success")))
        return result
    except FileNotFoundError:
        raise HTTPException(404, "project not found") from None
    except CompileError as e:
        record_from_output(str(e), success=False)
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
    run.serial_device = body.serialDevice
    run.serial_baud = body.baud
    run.expect = body.expect
    RUNS[rid] = run
    run.task = asyncio.create_task(run_agent(run))
    return {"id": rid, "run_id": rid}


@app.get("/api/runs")
def runs_list() -> list[dict[str, Any]]:
    live = [
        {"id": r.id, "project_id": r.project_id, "prompt": r.prompt, "status": r.status, "iteration": r.iteration}
        for r in RUNS.values()
    ]
    stored = list_runs()
    seen = {x["id"] for x in live}
    return live + [s for s in stored if s.get("id") not in seen]


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
async def approve(run_id: str, body: ApproveBody | None = None) -> dict[str, str]:
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    decision = (body.decision if body else "approved") or "approved"
    resolve_approval(run, decision, body.approvalId if body else None)
    return {"ok": "1", "decision": run.approval_decision}


@app.post("/api/agent/runs")
async def create_run_alias(body: CreateRunBody) -> dict[str, str]:
    return await create_run(body)

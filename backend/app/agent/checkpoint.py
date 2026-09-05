from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.config.settings import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not re.match(r"^[a-zA-Z0-9_\-]+$", run_id):
        raise ValueError(f"Invalid run_id: {run_id!r}")
    return run_id


def sanitize_project_id(project_id: str) -> str:
    if not isinstance(project_id, str) or not re.match(r"^[a-zA-Z0-9_\-]+$", project_id):
        raise ValueError(f"Invalid project_id: {project_id!r}")
    return project_id


@dataclass
class RunCheckpoint:
    run_id: str
    project_id: str
    prompt: str
    mode: str
    status: str = "running"  # running, paused, completed, failed, cancelled
    phase: str = "init"      # init, plan, reasoning, tool_call, compile, hardware_loop, done
    iteration: int = 0
    max_iterations: int = 10
    hardware_attempt: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_errors: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    snapshot_sha: str = ""
    action_plan: dict[str, Any] | None = None
    loaded_skills: list[dict[str, Any]] = field(default_factory=list)
    serial_device: str | None = None
    serial_baud: int = 115200
    expect: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    # Phase-aware resume & idempotency tracking
    step_id: str = ""
    completed_steps: list[str] = field(default_factory=list)
    pending_step: str | None = None
    idempotency_key: str = ""
    last_tool_call: dict[str, Any] | None = None
    last_tool_result: dict[str, Any] | None = None
    workspace_snapshot: str = ""
    executed_tools: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d.get("workspace_snapshot") and d.get("snapshot_sha"):
            d["workspace_snapshot"] = d["snapshot_sha"]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunCheckpoint:
        fields_set = {
            "run_id", "project_id", "prompt", "mode", "status", "phase",
            "iteration", "max_iterations", "hardware_attempt", "messages",
            "last_errors", "citations", "snapshot_sha", "action_plan",
            "loaded_skills", "serial_device", "serial_baud", "expect",
            "created_at", "updated_at",
            "step_id", "completed_steps", "pending_step", "idempotency_key",
            "last_tool_call", "last_tool_result", "workspace_snapshot",
            "executed_tools",
        }
        filtered = {k: v for k, v in data.items() if k in fields_set}
        if "workspace_snapshot" in filtered and not filtered.get("snapshot_sha"):
            filtered["snapshot_sha"] = filtered["workspace_snapshot"]
        if "snapshot_sha" in filtered and not filtered.get("workspace_snapshot"):
            filtered["workspace_snapshot"] = filtered["snapshot_sha"]
        return cls(**filtered)


def get_checkpoint_path(run_id: str, repo_root: Path | None = None) -> Path:
    safe_id = sanitize_run_id(run_id)
    root = repo_root or getattr(settings, "repo_root", Path.cwd())
    run_dir = (root / "runs" / safe_id).resolve()
    base_runs = (root / "runs").resolve()
    if base_runs not in run_dir.parents and run_dir != base_runs:
        raise ValueError(f"Run directory escapes runs base: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / "checkpoint.json"


def save_run_checkpoint(checkpoint: RunCheckpoint, repo_root: Path | None = None) -> Path:
    checkpoint.updated_at = _now()
    path = get_checkpoint_path(checkpoint.run_id, repo_root)
    path.write_text(json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    # Also persist to SQLite database
    try:
        from app.db import save_checkpoint_db
        save_checkpoint_db(checkpoint.run_id, checkpoint.project_id, checkpoint.to_dict())
    except Exception:
        pass

    return path


def load_run_checkpoint(run_id: str, repo_root: Path | None = None) -> RunCheckpoint | None:
    path = get_checkpoint_path(run_id, repo_root)
    cp: RunCheckpoint | None = None
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cp = RunCheckpoint.from_dict(data)
        except Exception:
            pass

    if cp is None:
        try:
            from app.db import load_checkpoint_db
            db_data = load_checkpoint_db(run_id)
            if db_data:
                cp = RunCheckpoint.from_dict(db_data)
        except Exception:
            pass

    if cp is not None:
        try:
            sanitize_project_id(cp.project_id)
        except ValueError:
            return None
        return cp

    return None

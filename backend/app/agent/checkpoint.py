from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.config.settings import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunCheckpoint:
        fields_set = {
            "run_id", "project_id", "prompt", "mode", "status", "phase",
            "iteration", "max_iterations", "hardware_attempt", "messages",
            "last_errors", "citations", "snapshot_sha", "action_plan",
            "loaded_skills", "serial_device", "serial_baud", "expect",
            "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in fields_set}
        return cls(**filtered)


def get_checkpoint_path(run_id: str, repo_root: Path | None = None) -> Path:
    root = repo_root or getattr(settings, "repo_root", Path.cwd())
    run_dir = root / "runs" / run_id
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
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return RunCheckpoint.from_dict(data)
        except Exception:
            pass

    try:
        from app.db import load_checkpoint_db
        db_data = load_checkpoint_db(run_id)
        if db_data:
            return RunCheckpoint.from_dict(db_data)
    except Exception:
        pass

    return None

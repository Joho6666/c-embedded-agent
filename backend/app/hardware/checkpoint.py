"""Stage checkpoint / resume for long hardware and agent runs.

A run declares an ordered stage list; every completed stage is persisted
with its result summary. After a crash, `pending_stages()` returns only the
unfinished tail — completed work is never redone.

Store: one JSON file per run key, `<project_root>/hardware-runs/checkpoint-<runKey>.json`
(the workspace-level store for project-less runs goes through the same API
with an explicit path).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StageCheckpoint:
    def __init__(self, run_key: str, stages: list[str], path: Path | None = None) -> None:
        if not stages:
            raise ValueError("checkpoint requires a non-empty stage list")
        self.run_key = run_key
        self.stages = list(stages)
        self.path = Path(path) if path else Path(f"checkpoint-{run_key}.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {"runKey": run_key, "stages": self.stages, "completed": {}, "status": "running"}
        if self.path.is_file():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and loaded.get("runKey") == run_key:
                    self._data = loaded
            except json.JSONDecodeError:
                pass

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def is_done(self, stage: str) -> bool:
        return stage in self._data.get("completed", {})

    def mark_done(self, stage: str, summary: Any = None) -> None:
        if stage not in self.stages:
            raise ValueError(f"unknown stage: {stage!r}")
        self._data.setdefault("completed", {})[stage] = {
            "summary": summary,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self._save()

    def pending_stages(self) -> list[str]:
        """Stages still to execute, in declared order."""
        return [s for s in self.stages if not self.is_done(s)]

    def completed_stages(self) -> list[str]:
        return [s for s in self.stages if self.is_done(s)]

    def summary_of(self, stage: str) -> Any:
        entry = (self._data.get("completed") or {}).get(stage)
        return entry.get("summary") if entry else None

    def finish(self, status: str) -> None:
        self._data["status"] = status
        self._data["finishedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._save()

    def reset(self) -> None:
        self._data["completed"] = {}
        self._data["status"] = "running"
        self._save()

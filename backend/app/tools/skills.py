from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import settings


def _path() -> Path:
    p = Path(__file__).resolve().parent.parent / "skills" / "stm32f103.json"
    return p


def list_skills() -> list[dict[str, Any]]:
    path = _path()
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def get_skill(sid: str) -> dict[str, Any] | None:
    for s in list_skills():
        if s.get("id") == sid:
            return s
    return None


def benchmark_wrap(raw: dict[str, Any]) -> dict[str, Any]:
    skipped = raw.get("skipped") if isinstance(raw.get("skipped"), list) else []
    compile_r = raw.get("compile_success_rate")
    first = raw.get("first_build_success_rate")
    auto = raw.get("auto_fix_success_rate")
    avg = raw.get("avg_iterations")
    has = isinstance(compile_r, (int, float)) or isinstance(first, (int, float))
    return {
        "available": True,
        "reason": None if has else (" · ".join(skipped) if skipped else "No benchmark data"),
        "mcu": "STM32F103",
        "tasks": raw.get("tasks") if isinstance(raw.get("tasks"), int) else raw.get("n"),
        "compileSuccess": compile_r if isinstance(compile_r, (int, float)) else None,
        "firstBuildSuccess": first if isinstance(first, (int, float)) else None,
        "autoFix": auto if isinstance(auto, (int, float)) else None,
        "avgIterations": avg if isinstance(avg, (int, float)) else None,
        "skipped": skipped,
        "bySkill": [],
        "models": [],
        "gcc": raw.get("gcc") if isinstance(raw.get("gcc"), bool) else None,
        "llm": raw.get("llm") if isinstance(raw.get("llm"), bool) else None,
    }


def repo_root() -> Path:
    return settings.repo_root

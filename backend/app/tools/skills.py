from __future__ import annotations

from typing import Any

from app.config.settings import settings
from app.agent.skill_router import SkillRouter
from app.agent.task_classifier import ContextLevel
from app.skills.registry import default_skill_registry


def list_skills() -> list[dict[str, Any]]:
    return [skill.to_dict() for skill in default_skill_registry().list(include_disabled=True)]


def get_skill(sid: str) -> dict[str, Any] | None:
    skill = default_skill_registry().get(sid, include_disabled=True)
    return skill.to_dict() if skill else None


def match_skills(
    prompt: str,
    *,
    platform: str = "stm32f103",
    context_level: ContextLevel | str = ContextLevel.DEEP,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selection = SkillRouter().select(prompt, platform=platform, context_level=context_level, limit=limit)
    return [skill.to_dict() for skill in selection.skills]


def skill_summary(skill: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": skill.get("id"),
        "name": skill.get("name"),
        "capabilities": skill.get("capabilities") or [],
        "pins": skill.get("pins") or [],
        "clocks": skill.get("clocks") or [],
        "halModules": skill.get("halModules") or [],
        "sourceFiles": skill.get("sourceFiles") or [],
        "irq": skill.get("irq") or [],
        "dma": skill.get("dma") or [],
        "initOrder": skill.get("initOrder") or [],
        "validators": [v.get("label") if isinstance(v, dict) else str(v) for v in (skill.get("validators") or [])],
        "knownErrors": [e.get("pattern") if isinstance(e, dict) else str(e) for e in (skill.get("knownErrors") or skill.get("known_errors") or [])],
        "goldenExamples": [g.get("title") or g.get("path") if isinstance(g, dict) else str(g) for g in (skill.get("goldenExamples") or skill.get("golden_examples") or [])],
        "knowledge": skill.get("knowledge") or skill.get("knowledgeCollections") or [],
    }


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

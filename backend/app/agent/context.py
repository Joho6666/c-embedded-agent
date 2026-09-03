from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agent.context_router import ContextRouter
from app.agent.task_classifier import TaskClassifier
from app.config.settings import settings
from app.platforms.registry import default_registry
from app.tools.filesystem import list_files
from app.tools.ioc import parse_ioc
from app.tools.skills import match_skills, skill_summary


def load_ioc_analysis(root: Path) -> dict[str, Any] | None:
    cached = root / "ioc-analysis.json"
    if cached.is_file():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    iocs = sorted(root.glob("*.ioc"))
    if not iocs:
        return None
    try:
        return parse_ioc(iocs[0].read_text(encoding="utf-8"), iocs[0].name)
    except OSError:
        return None


def led_from_ioc(ioc: dict[str, Any] | None) -> str:
    if not ioc:
        return ""
    for p in ioc.get("pins") or []:
        sig = str(p.get("signal") or "")
        label = str(p.get("mode") or "")
        pin = str(p.get("pin") or "")
        if "LED" in sig.upper() or "LED" in label.upper():
            return pin
    return ""


def build_context(
    root: Path,
    *,
    iteration: int,
    errors: list[dict[str, Any]] | None = None,
    knowledge: list[dict[str, Any]] | None = None,
    board: str | None = None,
    prompt: str = "",
    extra_skills: list[dict[str, Any]] | None = None,
    platform_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    files = []
    try:
        files = list_files(root)
    except OSError:
        files = []
    core = [
        f for f in files
        if f.endswith((".c", ".h")) and not f.startswith(("Drivers/", "Middlewares/", "build/"))
    ]
    if platform_context is None:
        registry = default_registry(settings.repo_root)
        resolution = registry.detect(root)
        if resolution.adapter is None:
            cached_ioc = load_ioc_analysis(root) or {}
            if cached_ioc.get("mcu"):
                resolution = registry.resolve_explicit(mcu=str(cached_ioc["mcu"]))
        platform_context = resolution.adapter.load_context(root) if resolution.adapter else {}
    facts = dict(platform_context.get("facts") or {})
    ioc = platform_context.get("ioc") or load_ioc_analysis(root)
    project_cfg: dict[str, Any] = {}
    pj = root / "project.json"
    if pj.is_file():
        try:
            project_cfg = json.loads(pj.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            project_cfg = {}
    led = led_from_ioc(ioc) or facts.get("led") or project_cfg.get("led")
    classification = TaskClassifier().classify(prompt, platform=facts.get("adapterId") or facts.get("platform"))
    skills = [skill_summary(s) for s in match_skills(prompt, context_level=classification.context_level)]
    for s in extra_skills or []:
        sid = s.get("id")
        if sid and sid not in {x.get("id") for x in skills}:
            skills.append(skill_summary(s) if "capabilities" in s else s)
    # IOC > Project Config > Board Profile > Default
    mcu = (ioc or {}).get("mcu") or project_cfg.get("mcu") or facts.get("mcu")
    board_name = (ioc or {}).get("board") or project_cfg.get("board") or board or facts.get("board")
    clock = (ioc or {}).get("clock") or {}
    pins = (ioc or {}).get("pins") or []
    pin_brief = [f"{p.get('pin')}={p.get('signal')}" for p in pins[:16]]
    legacy_context = {
        "mcu": mcu,
        "adapterId": facts.get("adapterId"),
        "platform": facts.get("platform"),
        "core": facts.get("core"),
        "flash_kb": facts.get("flashKb") or facts.get("flash_kb"),
        "ram_kb": facts.get("ramKb") or facts.get("ram_kb"),
        "framework": project_cfg.get("framework") or facts.get("framework"),
        "compiler": project_cfg.get("toolchain") or facts.get("toolchain"),
        "board": board_name,
        "led": led,
        "iteration": iteration,
        "project_tree": files,
        "relevant_files": core,
        "errors": errors or [],
        "knowledge": knowledge or [],
        "ioc": {
            "filename": (ioc or {}).get("filename"),
            "clockMhz": int((clock.get("sysclkHz") or 0) / 1_000_000) if clock.get("sysclkHz") else None,
            "hseMhz": int((clock.get("hseHz") or 0) / 1_000_000) if clock.get("hseHz") else None,
            "pins": pin_brief,
            "conflicts": (ioc or {}).get("conflicts") or [],
            "usart": [u.get("name") for u in (ioc or {}).get("usart") or []],
        }
        if ioc
        else None,
        "skills": skills,
        "project": {
            "id": project_cfg.get("id"),
            "name": project_cfg.get("name"),
            "framework": project_cfg.get("framework") or facts.get("framework"),
        }
        if project_cfg
        else None,
        "priority": "IOC > Project Config > Board Profile > Default",
    }
    routed = ContextRouter().route(legacy_context, level=classification.context_level)
    compact = dict(routed.context.pop("platform_facts", {}))
    compact.update(routed.context)
    compact["_routing"] = {
        "contextLevel": routed.level.value,
        "budget": routed.budget,
        "usedChars": routed.used_chars,
        "includedSources": list(routed.included_sources),
        "truncatedSources": list(routed.truncated_sources),
        "reasons": list(routed.reasons),
    }
    return compact


def context_prompt(ctx: dict[str, Any]) -> str:
    errs = ctx.get("errors") or []
    err_lines = []
    for e in errs[:8]:
        err_lines.append(
            f"- {e.get('source', 'gcc')} {e.get('file', '')}:{e.get('line', 0)} {e.get('severity', 'error')}: {e.get('message', '')}"
        )
    kn = ctx.get("knowledge") or []
    kn_lines = [f"- {k.get('source') or k.get('title')} {k.get('section', '')} p.{k.get('page', '')}" for k in kn]
    ioc = ctx.get("ioc")
    ioc_line = "(none)"
    if ioc:
        ioc_line = (
            f"file={ioc.get('filename')} SYSCLK={ioc.get('clockMhz')}MHz HSE={ioc.get('hseMhz')}MHz "
            f"pins={', '.join(ioc.get('pins') or [])} usart={', '.join(ioc.get('usart') or [])}"
        )
        if ioc.get("conflicts"):
            ioc_line += f" conflicts={ioc['conflicts']}"
    skills = ctx.get("skills") or []
    skill_lines = [
        f"- {s.get('name')}: {', '.join(s.get('capabilities') or [])}; validators={', '.join(s.get('validators') or [])}"
        for s in skills
    ]
    return (
        f"MCU={ctx.get('mcu')} Board={ctx.get('board')} LED={ctx.get('led')} "
        f"Framework={ctx.get('framework')} Compiler={ctx.get('compiler')} Iteration={ctx.get('iteration')}\n"
        f"IOC: {ioc_line}\n"
        f"Skills:\n" + ("\n".join(skill_lines) if skill_lines else "(none)") + "\n"
        f"Core files: {', '.join(ctx.get('relevant_files') or [])}\n"
        f"Recent errors:\n" + ("\n".join(err_lines) if err_lines else "(none)") + "\n"
        f"Knowledge:\n" + ("\n".join(kn_lines) if kn_lines else "(none)")
    )

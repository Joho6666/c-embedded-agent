from __future__ import annotations

from pathlib import Path
from typing import Any

from app.mcu.stm32f103 import MCU
from app.tools.filesystem import list_files


def build_context(
    root: Path,
    *,
    iteration: int,
    errors: list[dict[str, Any]] | None = None,
    knowledge: list[dict[str, Any]] | None = None,
    board: str = "Blue Pill",
) -> dict[str, Any]:
    files = []
    try:
        files = list_files(root)
    except OSError:
        files = []
    core = [f for f in files if f.startswith("Core/") and f.endswith((".c", ".h"))]
    return {
        "mcu": MCU["name"],
        "core": MCU["core"],
        "flash_kb": MCU["flash_kb"],
        "ram_kb": MCU["ram_kb"],
        "framework": "HAL",
        "compiler": "arm-none-eabi-gcc",
        "board": board,
        "led": "PC13",
        "iteration": iteration,
        "project_tree": files[:80],
        "relevant_files": core[:24],
        "errors": (errors or [])[:12],
        "knowledge": (knowledge or [])[:4],
    }


def context_prompt(ctx: dict[str, Any]) -> str:
    errs = ctx.get("errors") or []
    err_lines = []
    for e in errs[:8]:
        err_lines.append(
            f"- {e.get('source', 'gcc')} {e.get('file', '')}:{e.get('line', 0)} {e.get('severity', 'error')}: {e.get('message', '')}"
        )
    kn = ctx.get("knowledge") or []
    kn_lines = [f"- {k.get('source') or k.get('title')} {k.get('section', '')} p.{k.get('page', '')}" for k in kn]
    return (
        f"MCU={ctx.get('mcu')} Board={ctx.get('board')} LED={ctx.get('led')} "
        f"Framework={ctx.get('framework')} Compiler={ctx.get('compiler')} Iteration={ctx.get('iteration')}\n"
        f"Core files: {', '.join(ctx.get('relevant_files') or [])}\n"
        f"Recent errors:\n" + ("\n".join(err_lines) if err_lines else "(none)") + "\n"
        f"Knowledge:\n" + ("\n".join(kn_lines) if kn_lines else "(none)")
    )

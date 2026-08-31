#!/usr/bin/env python3
"""STM32F103 Agent vs baseline benchmark harness."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = Path(__file__).resolve().parent / "stm32f103"
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)


def gcc_ok() -> bool:
    return shutil.which("arm-none-eabi-gcc") is not None and shutil.which("make") is not None


def llm_ok() -> bool:
    return bool(os.environ.get("LLM_API_KEY") and os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_MODEL"))


def load_tasks() -> list[dict]:
    tasks = []
    for p in sorted(TASK_DIR.glob("*.json")):
        if p.name == "results.json":
            continue
        tasks.append(json.loads(p.read_text(encoding="utf-8")))
    return tasks


def run_build(project_root: Path) -> dict:
    from app.tools.compiler import CompileError, compile_project

    try:
        return compile_project(project_root)
    except CompileError as e:
        return {"success": False, "error": str(e), "exit_code": 127}


def baseline_write(project_root: Path, prompt: str) -> dict:
    """LLM dumps code with no tools — comparison only."""
    from app.services.llm import LLMError, chat
    import asyncio

    async def _go() -> str:
        data = await chat(
            [
                {"role": "system", "content": "只输出完整 main.c，不要解释。"},
                {"role": "user", "content": prompt},
            ]
        )
        return data["choices"][0]["message"].get("content") or ""

    try:
        text = asyncio.run(_go())
    except LLMError as e:
        return {"ok": False, "error": str(e)}
    main = project_root / "Core" / "Src" / "main.c"
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("c"):
            text = text[1:]
    main.write_text(text.strip() + "\n", encoding="utf-8")
    return {"ok": True}


def main() -> int:
    limit = int(os.environ.get("BENCH_LIMIT", "10"))
    tasks = load_tasks()[:limit]
    out = {
        "gcc": gcc_ok(),
        "llm": llm_ok(),
        "tasks": [],
        "first_build_success": 0,
        "auto_fix_success": 0,
        "compile_success": 0,
        "avg_iterations": 0.0,
        "skipped": [],
    }
    if not gcc_ok():
        out["skipped"].append("arm-none-eabi-gcc or make missing")
        (TASK_DIR / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        print("SKIP: ARM GCC not installed — not faking success")
        return 0
    if not llm_ok():
        out["skipped"].append("LLM not configured")
        # Still record that template itself builds.
        from app.workspace.manager import create_project, project_root
        from app.config.settings import settings

        meta = create_project("bench-template")
        result = run_build(project_root(meta["id"]))
        out["template_build"] = bool(result.get("success"))
        (TASK_DIR / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        print("SKIP: LLM not configured — template compile recorded only")
        return 0

    from app.workspace.manager import create_project, project_root
    from app.agent.runtime import AgentRun, run_agent
    import asyncio
    import uuid

    iterations = []
    for task in tasks:
        t0 = time.perf_counter()
        meta = create_project(task.get("id", "bench"))
        root = project_root(meta["id"])
        rid = f"run-{uuid.uuid4().hex[:8]}"
        run = AgentRun(rid, meta["id"], task["prompt"], "auto")
        asyncio.run(run_agent(run))
        first = next((e for e in run.events if e.get("type") == "compile"), None)
        last_ok = run.status == "success"
        item = {
            "id": task.get("id"),
            "prompt": task["prompt"],
            "status": run.status,
            "iterations": run.iteration,
            "first_build_ok": bool(first and first.get("status") == "success"),
            "success": last_ok,
            "seconds": round(time.perf_counter() - t0, 2),
        }
        out["tasks"].append(item)
        iterations.append(run.iteration)
        if item["first_build_ok"]:
            out["first_build_success"] += 1
        if last_ok:
            out["compile_success"] += 1
            if not item["first_build_ok"]:
                out["auto_fix_success"] += 1
        print(item)

    n = max(len(tasks), 1)
    out["first_build_success_rate"] = out["first_build_success"] / n
    out["compile_success_rate"] = out["compile_success"] / n
    out["avg_iterations"] = sum(iterations) / max(len(iterations), 1)
    (TASK_DIR / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "tasks"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

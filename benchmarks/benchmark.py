#!/usr/bin/env python3
"""STM32F103 Agent vs baseline benchmark harness."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = Path(__file__).resolve().parent / "stm32f103"
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)


def gcc_ok() -> bool:
    from app.tools.toolchain import prepend_toolchain_path

    prepend_toolchain_path()
    return shutil.which("arm-none-eabi-gcc") is not None and shutil.which("make") is not None


def llm_ok() -> bool:
    return bool(os.environ.get("LLM_API_KEY") and os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_MODEL"))


def load_tasks() -> list[dict]:
    tasks = []
    for p in sorted(TASK_DIR.glob("*.json")):
        if p.name in {"results.json", "latest-summary.json"}:
            continue
        task = json.loads(p.read_text(encoding="utf-8"))
        task.setdefault("domain", "PERIPHERAL_CONFIG")
        task.setdefault("level", "regression")
        task.setdefault("inject", [])
        tasks.append(task)
    return tasks


def apply_inject(project_root: Path, injects: list[dict]) -> list[str]:
    """Apply injected faults (COMPILE_REPAIR / DEBUGGING tasks). Returns notes."""
    applied = []
    for spec in injects or []:
        try:
            f = project_root / spec["file"]
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8")
            if spec["find"] not in text:
                continue
            n = int(spec.get("count", 1))
            text = text.replace(spec["find"], spec["replace"], n)
            f.write_text(text, encoding="utf-8")
            applied.append(f"{spec['file']}:{spec['find'][:30]}")
        except (OSError, KeyError):
            continue
    return applied


def domain_rates(tasks: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for t in tasks:
        dom = t.get("domain") or "unknown"
        bucket = out.setdefault(dom, {"tasks": 0, "compile": 0, "semantic": 0})
        bucket["tasks"] += 1
        if t.get("success"):
            bucket["compile"] += 1
        if t.get("semantic_ok"):
            bucket["semantic"] += 1
    for dom, b in out.items():
        n = max(b["tasks"], 1)
        b["compileSuccess"] = round(b["compile"] / n, 4)
        b["semanticSuccess"] = round(b["semantic"] / n, 4)
    return out


def level_rates(tasks: list[dict]) -> dict:
    out = {}
    for lvl in ("regression", "capability"):
        sub = [t for t in tasks if t.get("level") == lvl]
        n = max(len(sub), 1)
        out[lvl] = {
            "tasks": len(sub),
            "compileSuccess": round(sum(1 for t in sub if t.get("success")) / n, 4),
            "semanticSuccess": round(sum(1 for t in sub if t.get("semantic_ok")) / n, 4),
        }
    return out


def run_build(project_root: Path) -> dict:
    from app.tools.compiler import CompileError, compile_project

    try:
        return compile_project(project_root)
    except CompileError as e:
        return {"success": False, "error": str(e), "exit_code": 127}


def semantic_ok(project_root: Path, prompt: str) -> bool:
    from app.validation import validate_project

    r = validate_project(project_root, prompt)
    return bool(r.get("passed")) or float(r.get("score") or 0) >= 0.8


def agent_semantic_ok(run_events: list[dict]) -> bool | None:
    """Reuse the validation the agent already computed (None → caller must recompute)."""
    for e in reversed(run_events):
        if e.get("type") != "validation":
            continue
        try:
            desc = json.loads(e.get("description") or "{}")
            s = desc.get("semantic") or {}
            return bool(s.get("passed")) or float(s.get("score") or 0) >= 0.8
        except (ValueError, TypeError):
            return None
    return None


async def baseline_write(project_root: Path, prompt: str) -> dict:
    """LLM dumps code with no tools — comparison only."""
    from app.services.llm import LLMError, chat

    try:
        data = await chat(
            [
                {"role": "system", "content": "只输出完整 main.c，不要解释。不要使用知识库、Skill、Error Memory 或编译修复循环。"},
                {"role": "user", "content": prompt},
            ]
        )
    except LLMError as e:
        return {"ok": False, "error": str(e), "input_tokens": 0, "output_tokens": 0}
    text = data["choices"][0]["message"].get("content") or ""
    usage = data.get("usage") or {}
    main = project_root / "Core" / "Src" / "main.c"
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("c"):
            text = text[1:]
    main.write_text(text.strip() + "\n", encoding="utf-8")
    return {
        "ok": True,
        "input_tokens": int(usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("completion_tokens") or 0),
    }


def empty_summary(*, gcc: bool, llm: bool, skipped: list[str], model: str) -> dict:
    return {
        "model": model,
        "tasks": 0,
        "firstBuildSuccess": 0.0,
        "finalCompileSuccess": 0.0,
        "autoFixSuccess": 0.0,
        "semanticValidation": 0.0,
        "avgIterations": 0.0,
        "avgLatency": 0.0,
        "inputTokens": 0,
        "outputTokens": 0,
        "gcc": gcc,
        "llm": llm,
        "skipped": skipped,
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    from app.config.settings import settings

    limit_raw = os.environ.get("BENCH_LIMIT")
    tasks = load_tasks()
    if limit_raw:
        tasks = tasks[: int(limit_raw)]
    model = os.environ.get("LLM_MODEL") or settings.llm_model or ""
    out = {
        "gcc": gcc_ok(),
        "llm": llm_ok(),
        "model": model,
        "tasks": [],
        "first_build_success": 0,
        "auto_fix_success": 0,
        "compile_success": 0,
        "semantic_success": 0,
        "avg_iterations": 0.0,
        "skipped": [],
    }
    summary_path = TASK_DIR / "latest-summary.json"
    comparison_path = ROOT / "benchmarks" / "comparison-summary.json"

    if not gcc_ok():
        skipped = ["arm-none-eabi-gcc or make missing"]
        out["skipped"] = skipped
        write_json(TASK_DIR / "results.json", out)
        write_json(summary_path, empty_summary(gcc=False, llm=llm_ok(), skipped=skipped, model=model))
        write_json(comparison_path, {"skipped": skipped, "reason": "toolchain missing — not faking scores"})
        print(json.dumps(out, indent=2))
        print("SKIP: ARM GCC not installed — not faking success")
        return 0
    if not llm_ok():
        skipped = ["LLM not configured"]
        from app.workspace.manager import create_project, project_root

        meta = create_project("bench-template")
        result = run_build(project_root(meta["id"]))
        out["skipped"] = skipped
        out["template_build"] = bool(result.get("success"))
        write_json(TASK_DIR / "results.json", out)
        write_json(summary_path, empty_summary(gcc=True, llm=False, skipped=skipped, model=model))
        write_json(comparison_path, {"skipped": skipped, "reason": "LLM not configured — not faking Agent vs Baseline"})
        print(json.dumps(out, indent=2))
        print("SKIP: LLM not configured — template compile recorded only")
        return 0

    from app.agent.runtime import RUNS, AgentRun, run_agent
    from app.services.llm import close_client
    from app.workspace.manager import create_project, project_root

    results_path = TASK_DIR / "results.json"
    parallel = max(1, int(os.environ.get("BENCH_PARALLEL") or "1"))
    stats = {
        "iterations": [],
        "latencies": [],
        "in_tokens": 0,
        "out_tokens": 0,
        "baseline_compile": 0,
        "baseline_valid": 0,
        "baseline_tokens": 0,
        "baseline_latency": 0.0,
        "agent_compile": 0,
        "agent_valid": 0,
    }

    async def _run_task(task: dict) -> None:
        prompt = task["prompt"]
        # --- Baseline: prompt → write main.c → build (no knowledge/skills/error memory/fix loop)
        b0 = time.perf_counter()
        bmeta = create_project(f"base-{task.get('id', 'bench')}")
        broot = project_root(bmeta["id"])
        bw = await baseline_write(broot, prompt)
        b_build = run_build(broot) if bw.get("ok") else {"success": False}
        b_sec = time.perf_counter() - b0
        b_ok = bool(b_build.get("success"))
        b_sem = semantic_ok(broot, prompt) if b_ok else False
        stats["baseline_tokens"] += int(bw.get("input_tokens") or 0) + int(bw.get("output_tokens") or 0)
        stats["baseline_latency"] += b_sec
        if b_ok:
            stats["baseline_compile"] += 1
        if b_sem:
            stats["baseline_valid"] += 1

        # --- Agent
        t0 = time.perf_counter()
        meta = create_project(task.get("id", "bench"))
        root = project_root(meta["id"])
        injected = apply_inject(root, task.get("inject") or [])
        rid = f"run-{uuid.uuid4().hex[:8]}"
        run = AgentRun(rid, meta["id"], prompt, "auto")
        await run_agent(run)
        RUNS.pop(rid, None)
        first = next((e for e in run.events if e.get("type") == "compile"), None)
        last_ok = run.status == "success"
        sem = agent_semantic_ok(run.events)
        if sem is None:
            sem = semantic_ok(root, prompt) if last_ok else False
        seconds = round(time.perf_counter() - t0, 2)
        item = {
            "id": task.get("id"),
            "prompt": prompt,
            "domain": task.get("domain"),
            "level": task.get("level"),
            "injected": injected,
            "status": run.status,
            "iterations": run.iteration,
            "first_build_ok": bool(first and first.get("status") == "success"),
            "success": last_ok,
            "semantic_ok": sem,
            "seconds": seconds,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "baseline_success": b_ok,
            "baseline_semantic": b_sem,
            "baseline_seconds": round(b_sec, 2),
        }
        out["tasks"].append(item)
        stats["iterations"].append(run.iteration)
        stats["latencies"].append(seconds)
        stats["in_tokens"] += run.input_tokens
        stats["out_tokens"] += run.output_tokens
        if item["first_build_ok"]:
            out["first_build_success"] += 1
        if last_ok:
            out["compile_success"] += 1
            stats["agent_compile"] += 1
            if not item["first_build_ok"]:
                out["auto_fix_success"] += 1
        if sem:
            out["semantic_success"] += 1
            stats["agent_valid"] += 1

        # --- Outcome Memory: one row per real run (never written without one)
        try:
            from app.tools.outcome_memory import record_outcome

            record_outcome(
                run_id=rid,
                task_id=str(task.get("id") or ""),
                task_type="benchmark",
                domain=task.get("domain"),
                model=model or None,
                attempts=max(1, run.iteration),
                repair_count=max(0, run.iteration - 1) if not item["first_build_ok"] and last_ok else 0,
                input_tokens=run.input_tokens,
                output_tokens=run.output_tokens,
                elapsed_s=seconds,
                build_success=last_ok,
                simulation_success=False,
                hardware_success=False,  # benchmark runs are compile/semantic only
                detail={"semantic_ok": sem, "injected": injected, "baseline_success": b_ok},
            )
        except Exception as e:  # noqa: BLE001 — recording must not break the bench
            out.setdefault("outcome_memory_errors", []).append(str(e))
        write_json(results_path, out)  # incremental: a crash mid-run keeps finished tasks
        print(item)

    async def _run_all() -> None:
        try:
            if parallel <= 1:
                for task in tasks:
                    await _run_task(task)
            else:
                sem = asyncio.Semaphore(parallel)

                async def _one(t: dict) -> None:
                    async with sem:
                        await _run_task(t)

                await asyncio.gather(*(_one(t) for t in tasks))
        finally:
            await close_client()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_all())
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    n = max(len(tasks), 1)
    out["first_build_success_rate"] = out["first_build_success"] / n
    out["compile_success_rate"] = out["compile_success"] / n
    out["auto_fix_success_rate"] = out["auto_fix_success"] / n
    out["semantic_success_rate"] = out["semantic_success"] / n
    out["avg_iterations"] = sum(stats["iterations"]) / max(len(stats["iterations"]), 1)
    out["domainRates"] = domain_rates(out["tasks"])
    out["levelRates"] = level_rates(out["tasks"])
    write_json(TASK_DIR / "results.json", out)

    summary = {
        "model": model,
        "tasks": len(tasks),
        "firstBuildSuccess": out["first_build_success"] / n,
        "finalCompileSuccess": out["compile_success"] / n,
        "autoFixSuccess": out["auto_fix_success"] / n,
        "semanticValidation": out["semantic_success"] / n,
        "avgIterations": out["avg_iterations"],
        "avgLatency": sum(stats["latencies"]) / max(len(stats["latencies"]), 1),
        "inputTokens": stats["in_tokens"],
        "outputTokens": stats["out_tokens"],
        "domainRates": out["domainRates"],
        "levelRates": out["levelRates"],
        "gcc": True,
        "llm": True,
        "skipped": [],
    }
    write_json(summary_path, summary)

    comparison = {
        "tasks": len(tasks),
        "model": model,
        "baselineCompileSuccess": stats["baseline_compile"] / n,
        "agentCompileSuccess": stats["agent_compile"] / n,
        "baselineValidation": stats["baseline_valid"] / n,
        "agentValidation": stats["agent_valid"] / n,
        "baselineTokens": stats["baseline_tokens"],
        "agentTokens": stats["in_tokens"] + stats["out_tokens"],
        "baselineLatency": stats["baseline_latency"] / n,
        "agentLatency": sum(stats["latencies"]) / n,
        "improvementCompile": (stats["agent_compile"] - stats["baseline_compile"]) / n,
        "improvementValidation": (stats["agent_valid"] - stats["baseline_valid"]) / n,
        "skipped": [],
    }
    write_json(comparison_path, comparison)
    print(json.dumps({k: out[k] for k in out if k != "tasks"}, indent=2))
    print(json.dumps(summary, indent=2))
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

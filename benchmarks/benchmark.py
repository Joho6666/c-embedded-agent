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
RUNS_PER_TASK = int(os.environ.get("BENCH_RUNS", "1"))
OUTPUT_BUDGET = int(os.environ.get("BENCH_OUTPUT_TOKENS", "2048"))
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)


def gcc_ok() -> bool:
    from app.tools.toolchain import prepend_toolchain_path

    prepend_toolchain_path()
    return shutil.which("arm-none-eabi-gcc") is not None and shutil.which("make") is not None


def llm_ok() -> bool:
    from app.config.settings import settings

    return bool(settings.llm_api_key and settings.llm_base_url and settings.llm_model)


def load_tasks() -> list[dict]:
    tasks = []
    for p in sorted(TASK_DIR.glob("*.json")):
        if p.name in {"results.json", "latest-summary.json"}:
            continue
        task = json.loads(p.read_text(encoding="utf-8"))
        required = {"id", "prompt", "platform", "category", "fixture", "oracle", "requirements", "environment", "evidence"}
        missing = required - task.keys()
        if missing:
            raise ValueError(f"{p.name}: missing benchmark fields {sorted(missing)}")
        tasks.append(task)
    return tasks


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


async def agent_chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Pin the Agent arm to the same generation controls as the baseline."""
    from app.services.llm import chat

    return await chat(
        messages,
        tools,
        temperature=0,
        max_tokens=OUTPUT_BUDGET,
    )


def baseline_write(project_root: Path, prompt: str) -> dict:
    """LLM dumps code with no tools — comparison only."""
    from app.services.llm import LLMError, chat
    import asyncio

    async def _go() -> tuple[str, dict]:
        data = await chat(
            [
                {"role": "system", "content": "只输出完整 main.c，不要解释。不要使用知识库、Skill、Error Memory 或编译修复循环。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=OUTPUT_BUDGET,
        )
        text = data["choices"][0]["message"].get("content") or ""
        usage = data.get("usage") or {}
        return text, usage

    try:
        text, usage = asyncio.run(_go())
    except LLMError as e:
        return {"ok": False, "error": str(e), "input_tokens": 0, "output_tokens": 0}
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
        "status": "SKIPPED",
        "model": model,
        "tasks": 0,
        "firstBuildSuccess": None,
        "finalCompileSuccess": None,
        "autoFixSuccess": None,
        "semanticValidation": None,
        "avgIterations": None,
        "avgLatency": None,
        "inputTokens": 0,
        "outputTokens": 0,
        "gcc": gcc,
        "llm": llm,
        "skipped": skipped,
        "environment": {"temperature": 0, "outputBudget": OUTPUT_BUDGET, "runsPerTask": RUNS_PER_TASK},
        "evidence": [],
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
        "schema_version": 2,
        "status": "NOT RUN",
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
        "environment": {
            "temperature": 0,
            "output_budget": OUTPUT_BUDGET,
            "runs_per_task": RUNS_PER_TASK,
            "python": sys.version.split()[0],
        },
        "evidence": [],
    }
    summary_path = TASK_DIR / "latest-summary.json"
    comparison_path = ROOT / "benchmarks" / "comparison-summary.json"

    missing = []
    if not out["gcc"]:
        missing.append("arm-none-eabi-gcc or make missing")
    if not out["llm"]:
        missing.append("LLM not configured")
    if missing:
        skipped = missing
        out["skipped"] = skipped
        out["status"] = "SKIPPED"
        out.update(
            {
                "first_build_success_rate": None,
                "compile_success_rate": None,
                "auto_fix_success_rate": None,
                "semantic_success_rate": None,
                "avg_iterations": None,
            }
        )
        write_json(TASK_DIR / "results.json", out)
        write_json(summary_path, empty_summary(gcc=out["gcc"], llm=out["llm"], skipped=skipped, model=model))
        write_json(
            comparison_path,
            {
                "status": "SKIPPED",
                "tasks": 0,
                "model": model,
                "baselineCompileSuccess": None,
                "agentCompileSuccess": None,
                "baselineValidation": None,
                "agentValidation": None,
                "skipped": skipped,
                "reason": "; ".join(skipped) + " — not faking scores",
                "environment": out["environment"],
                "evidence": [],
            },
        )
        print(json.dumps(out, indent=2))
        print(f"SKIP: {'; '.join(skipped)} — benchmark not run")
        return 0

    from app.workspace.manager import create_project, project_root
    from app.agent import runtime as agent_runtime
    import asyncio
    import uuid

    # Runtime keeps its backwards-compatible call signature; the harness pins the
    # exact same generation settings used by the plain-LLM baseline.
    agent_runtime.chat = agent_chat
    AgentRun = agent_runtime.AgentRun
    run_agent = agent_runtime.run_agent

    iterations = []
    latencies = []
    in_tokens = 0
    out_tokens = 0
    baseline_compile = 0
    baseline_valid = 0
    baseline_tokens = 0
    baseline_latency = 0.0
    agent_compile = 0
    agent_valid = 0

    for task in tasks:
        prompt = task["prompt"]
        # --- Baseline: prompt → write main.c → build (no knowledge/skills/error memory/fix loop)
        b0 = time.perf_counter()
        bmeta = create_project(f"base-{task.get('id', 'bench')}")
        broot = project_root(bmeta["id"])
        bw = baseline_write(broot, prompt)
        b_build = run_build(broot) if bw.get("ok") else {"success": False}
        b_sec = time.perf_counter() - b0
        b_ok = bool(b_build.get("success"))
        b_sem = semantic_ok(broot, prompt) if b_ok else False
        baseline_tokens += int(bw.get("input_tokens") or 0) + int(bw.get("output_tokens") or 0)
        baseline_latency += b_sec
        if b_ok:
            baseline_compile += 1
        if b_sem:
            baseline_valid += 1

        # --- Agent
        t0 = time.perf_counter()
        meta = create_project(task.get("id", "bench"))
        root = project_root(meta["id"])
        rid = f"run-{uuid.uuid4().hex[:8]}"
        run = AgentRun(rid, meta["id"], prompt, "auto")
        asyncio.run(run_agent(run))
        first = next((e for e in run.events if e.get("type") == "compile"), None)
        last_ok = run.status == "success"
        sem = semantic_ok(root, prompt) if last_ok else False
        seconds = round(time.perf_counter() - t0, 2)
        item = {
            "id": task.get("id"),
            "prompt": prompt,
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
            "platform": task["platform"],
            "category": task["category"],
            "fixture": task["fixture"],
            "oracle": task["oracle"],
            "requirements": task["requirements"],
            "environment": task["environment"],
            "evidence": task["evidence"],
        }
        out["tasks"].append(item)
        iterations.append(run.iteration)
        latencies.append(seconds)
        in_tokens += run.input_tokens
        out_tokens += run.output_tokens
        if item["first_build_ok"]:
            out["first_build_success"] += 1
        if last_ok:
            out["compile_success"] += 1
            agent_compile += 1
            if not item["first_build_ok"]:
                out["auto_fix_success"] += 1
        if sem:
            out["semantic_success"] += 1
            agent_valid += 1
        print(item)

    n = max(len(tasks), 1)
    out["first_build_success_rate"] = out["first_build_success"] / n
    out["compile_success_rate"] = out["compile_success"] / n
    out["auto_fix_success_rate"] = out["auto_fix_success"] / n
    out["semantic_success_rate"] = out["semantic_success"] / n
    out["status"] = "PASS"
    out["avg_iterations"] = sum(iterations) / max(len(iterations), 1)
    write_json(TASK_DIR / "results.json", out)

    summary = {
        "status": "PASS",
        "model": model,
        "tasks": len(tasks),
        "firstBuildSuccess": out["first_build_success"] / n,
        "finalCompileSuccess": out["compile_success"] / n,
        "autoFixSuccess": out["auto_fix_success"] / n,
        "semanticValidation": out["semantic_success"] / n,
        "avgIterations": out["avg_iterations"],
        "avgLatency": sum(latencies) / max(len(latencies), 1),
        "inputTokens": in_tokens,
        "outputTokens": out_tokens,
        "gcc": True,
        "llm": True,
        "skipped": [],
        "environment": out["environment"],
        "evidence": [{"kind": "raw-results", "path": "benchmarks/stm32f103/results.json"}],
    }
    write_json(summary_path, summary)

    comparison = {
        "status": "PASS",
        "tasks": len(tasks),
        "model": model,
        "baselineCompileSuccess": baseline_compile / n,
        "agentCompileSuccess": agent_compile / n,
        "baselineValidation": baseline_valid / n,
        "agentValidation": agent_valid / n,
        "baselineTokens": baseline_tokens,
        "agentTokens": in_tokens + out_tokens,
        "baselineLatency": baseline_latency / n,
        "agentLatency": sum(latencies) / n,
        "improvementCompile": (agent_compile - baseline_compile) / n,
        "improvementValidation": (agent_valid - baseline_valid) / n,
        "skipped": [],
        "environment": out["environment"],
        "evidence": [{"kind": "raw-results", "path": "benchmarks/stm32f103/results.json"}],
    }
    write_json(comparison_path, comparison)
    print(json.dumps({k: out[k] for k in out if k != "tasks"}, indent=2))
    print(json.dumps(summary, indent=2))
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

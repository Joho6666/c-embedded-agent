#!/usr/bin/env python3
"""STM32F103 Agent vs Plain LLM benchmark harness with reproducible environment tracking."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = Path(__file__).resolve().parent / "stm32f103"
RESULTS_BASE = ROOT / "benchmark-results"
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
    """Plain LLM dumps code with no tools — comparison baseline only."""
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
    main_file = project_root / "Core" / "Src" / "main.c"
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("c") or text.startswith("C"):
            text = text[1:]
    main_file.write_text(text.strip() + "\n", encoding="utf-8")
    return {
        "ok": True,
        "input_tokens": int(usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("completion_tokens") or 0),
    }


def get_git_commit_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def get_node_version() -> str | None:
    try:
        proc = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None
    except Exception:
        return None


def get_arm_gcc_version() -> str | None:
    from app.tools.toolchain import prepend_toolchain_path

    prepend_toolchain_path()
    try:
        proc = subprocess.run(["arm-none-eabi-gcc", "--version"], capture_output=True, text=True, timeout=5, check=False)
        return proc.stdout.splitlines()[0].strip() if proc.returncode == 0 else None
    except Exception:
        return None


def get_espidf_version() -> str | None:
    try:
        proc = subprocess.run(["idf.py", "--version"], capture_output=True, text=True, timeout=5, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None
    except Exception:
        return None


def compute_task_hash(tasks: list[dict]) -> str:
    hasher = hashlib.sha256()
    for t in sorted(tasks, key=lambda x: str(x.get("id"))):
        hasher.update(str(t.get("id")).encode())
        hasher.update(str(t.get("prompt")).encode())
    return hasher.hexdigest()[:16]


def compute_project_hash() -> str:
    hasher = hashlib.sha256()
    template = ROOT / "templates" / "stm32f103_hal_official"
    for p in sorted(template.glob("Core/**/*.*")):
        if p.is_file():
            hasher.update(p.read_bytes())
    return hasher.hexdigest()[:16]


def collect_environment_metadata(model: str, base_url: str | None) -> dict[str, Any]:
    host = urlparse(base_url).hostname if base_url else None
    return {
        "gitCommitSha": get_git_commit_sha(),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "node": get_node_version(),
        "armGccVersion": get_arm_gcc_version(),
        "espIdfVersion": get_espidf_version() or "not_installed",
        "model": model,
        "baseUrlHost": host,
        "temperature": 0,
        "topP": 1.0,
        "reasoningSetting": None,
        "maxTokens": OUTPUT_BUDGET,
        "runsPerTask": RUNS_PER_TASK,
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def empty_summary(*, gcc: bool, llm: bool, skipped: list[str], model: str, env: dict[str, Any]) -> dict:
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
        "estimatedCost": 0.0,
        "gcc": gcc,
        "llm": llm,
        "skipped": skipped,
        "reason": "; ".join(skipped) if skipped else "Evaluation skipped",
        "environment": env,
        "evidence": [],
    }


def main() -> int:
    from app.config.settings import settings

    limit_raw = os.environ.get("BENCH_LIMIT")
    tasks = load_tasks()
    if limit_raw:
        tasks = tasks[: int(limit_raw)]

    model = os.environ.get("LLM_MODEL") or settings.llm_model or ""
    base_url = settings.llm_base_url
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    run_dir = RESULTS_BASE / f"run-{timestamp}"

    env_meta = collect_environment_metadata(model, base_url)
    env_meta["taskHash"] = compute_task_hash(tasks)
    env_meta["projectHash"] = compute_project_hash()

    summary_path = TASK_DIR / "latest-summary.json"
    comparison_path = ROOT / "benchmarks" / "comparison-summary.json"

    missing = []
    if not gcc_ok():
        missing.append("arm-none-eabi-gcc or make missing")
    if not llm_ok():
        missing.append("LLM not configured")

    if missing:
        skipped = missing
        out = {
            "schema_version": 2,
            "status": "SKIPPED",
            "gcc": gcc_ok(),
            "llm": llm_ok(),
            "model": model,
            "tasks": [],
            "first_build_success": None,
            "auto_fix_success": None,
            "compile_success": None,
            "semantic_success": None,
            "avg_iterations": None,
            "skipped": skipped,
            "environment": env_meta,
            "evidence": [],
        }
        write_json(TASK_DIR / "results.json", out)
        summ = empty_summary(gcc=out["gcc"], llm=out["llm"], skipped=skipped, model=model, env=env_meta)
        write_json(summary_path, summ)
        comp = {
            "status": "SKIPPED",
            "tasks": 0,
            "model": model,
            "baselineCompileSuccess": None,
            "agentCompileSuccess": None,
            "baselineValidation": None,
            "agentValidation": None,
            "improvementCompile": None,
            "improvementValidation": None,
            "skipped": skipped,
            "reason": "; ".join(skipped) + " — not faking Agent vs Baseline",
            "environment": env_meta,
            "evidence": [],
        }
        write_json(comparison_path, comp)

        # Also write structured run artifact folder
        write_json(run_dir / "config.json", {"limit": limit_raw, "tasks": len(tasks), "model": model})
        write_json(run_dir / "environment.json", env_meta)
        write_json(run_dir / "summary.json", summ)
        write_json(run_dir / "comparison.json", comp)

        print(json.dumps(summ, indent=2))
        print(f"SKIP: {'; '.join(skipped)} — benchmark not run")
        return 0

    from app.workspace.manager import create_project, project_root
    from app.agent import runtime as agent_runtime
    import asyncio
    import uuid

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
    baseline_latencies = []
    agent_compile = 0
    agent_valid = 0

    baseline_runs: list[dict] = []
    agent_runs: list[dict] = []
    failures: list[dict] = []

    out = {
        "schema_version": 2,
        "status": "RUNNING",
        "gcc": True,
        "llm": True,
        "model": model,
        "tasks": [],
        "first_build_success": 0,
        "auto_fix_success": 0,
        "compile_success": 0,
        "semantic_success": 0,
        "avg_iterations": 0.0,
        "skipped": [],
        "environment": env_meta,
        "evidence": [],
    }

    for task in tasks:
        prompt = task["prompt"]
        tid = task.get("id", "bench")

        # 1. Baseline: Prompt -> write main.c -> build (no tools, no skills, no error memory, no fix loop)
        b0 = time.perf_counter()
        bmeta = create_project(f"base-{tid}")
        broot = project_root(bmeta["id"])
        bw = baseline_write(broot, prompt)
        b_build = run_build(broot) if bw.get("ok") else {"success": False}
        b_sec = round(time.perf_counter() - b0, 2)
        b_ok = bool(b_build.get("success"))
        b_sem = semantic_ok(broot, prompt) if b_ok else False
        b_tok = int(bw.get("input_tokens") or 0) + int(bw.get("output_tokens") or 0)
        baseline_tokens += b_tok
        baseline_latencies.append(b_sec)
        if b_ok:
            baseline_compile += 1
        if b_sem:
            baseline_valid += 1

        baseline_runs.append({
            "id": tid,
            "compile_success": b_ok,
            "semantic_success": b_sem,
            "latency": b_sec,
            "tokens": b_tok,
            "error": b_build.get("error"),
        })

        # 2. C-Embedded Agent: full capabilities
        t0 = time.perf_counter()
        meta = create_project(f"agent-{tid}")
        root = project_root(meta["id"])
        rid = f"run-{uuid.uuid4().hex[:8]}"
        run = AgentRun(rid, meta["id"], prompt, "auto")
        asyncio.run(run_agent(run))
        first = next((e for e in run.events if e.get("type") == "compile"), None)
        last_ok = run.status == "success"
        sem = semantic_ok(root, prompt) if last_ok else False
        seconds = round(time.perf_counter() - t0, 2)

        item = {
            "id": tid,
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
            "baseline_seconds": b_sec,
            "platform": task["platform"],
            "category": task["category"],
            "fixture": task["fixture"],
            "oracle": task["oracle"],
            "requirements": task["requirements"],
            "environment": task["environment"],
            "evidence": task["evidence"],
        }
        out["tasks"].append(item)
        agent_runs.append(item)

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
        else:
            failures.append(item)
        if sem:
            out["semantic_success"] += 1
            agent_valid += 1

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
        "totalTokens": in_tokens + out_tokens,
        "estimatedCost": round((in_tokens * 0.000001) + (out_tokens * 0.000002), 4),
        "gcc": True,
        "llm": True,
        "skipped": [],
        "environment": env_meta,
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
        "baselineLatency": sum(baseline_latencies) / n,
        "agentLatency": sum(latencies) / n,
        "improvementCompile": (agent_compile - baseline_compile) / n,
        "improvementValidation": (agent_valid - baseline_valid) / n,
        "skipped": [],
        "environment": env_meta,
        "evidence": [{"kind": "raw-results", "path": "benchmarks/stm32f103/results.json"}],
    }
    write_json(comparison_path, comparison)

    # Persist structured benchmark run artifacts
    write_json(run_dir / "config.json", {"limit": limit_raw, "tasks": len(tasks), "model": model})
    write_json(run_dir / "environment.json", env_meta)
    write_json(run_dir / "baseline.json", baseline_runs)
    write_json(run_dir / "agent.json", agent_runs)
    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "comparison.json", comparison)
    if failures:
        write_json(run_dir / "failures" / "failed_tasks.json", failures)

    print(json.dumps(summary, indent=2))
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

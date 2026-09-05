#!/usr/bin/env python3
"""STM32F103 Agent vs Plain LLM benchmark harness with reproducible environment tracking."""
from __future__ import annotations

import argparse
import datetime
import difflib
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

FAILURE_TAXONOMY = (
    "LLM_GENERATION_ERROR",
    "SYNTAX_ERROR",
    "COMPILE_ERROR",
    "LINK_ERROR",
    "STATIC_VALIDATION_ERROR",
    "SEMANTIC_ERROR",
    "TOOL_ERROR",
    "TIMEOUT",
    "AGENT_LOOP_LIMIT",
    "HARDWARE_UNAVAILABLE",
)


def classify_failure(
    *,
    error: str | None = None,
    compiler_logs: str = "",
    exit_code: int | None = None,
    validation_score: float | None = None,
    iterations: int = 0,
    max_iterations: int = 10,
    requires_hardware: bool = False,
    has_hardware: bool = False,
) -> str:
    if error:
        err_lower = error.lower()
        if "timeout" in err_lower or "timed out" in err_lower:
            return "TIMEOUT"
        if "hardware" in err_lower:
            return "HARDWARE_UNAVAILABLE"
        if "tool" in err_lower:
            return "TOOL_ERROR"
        return "LLM_GENERATION_ERROR"
    if requires_hardware and not has_hardware:
        return "HARDWARE_UNAVAILABLE"
    if exit_code is not None and exit_code != 0:
        logs_lower = compiler_logs.lower()
        if any(k in logs_lower for k in ("multiple definition", "ld returned", "undefined reference", "relocation")):
            return "LINK_ERROR"
        if any(k in logs_lower for k in ("syntax error", "expected", "undeclared", "unknown type name")):
            return "SYNTAX_ERROR"
        return "COMPILE_ERROR"
    if iterations >= max_iterations:
        return "AGENT_LOOP_LIMIT"
    if validation_score is not None and validation_score < 0.8:
        return "STATIC_VALIDATION_ERROR"
    return "SEMANTIC_ERROR"


def save_task_evidence(
    run_dir: Path,
    tid: str,
    prompt: str,
    starting_project_meta: dict,
    baseline_code: str,
    agent_code: str,
    initial_code: str,
    compiler_logs: str,
    validator_logs: str,
    metrics: dict,
) -> Path:
    task_dir = run_dir / f"task-{tid}"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (task_dir / "starting_project.json").write_text(json.dumps(starting_project_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (task_dir / "baseline_output.c").write_text(baseline_code, encoding="utf-8")
    (task_dir / "agent_output.c").write_text(agent_code, encoding="utf-8")
    (task_dir / "compiler_logs.txt").write_text(compiler_logs, encoding="utf-8")
    (task_dir / "validator_logs.txt").write_text(validator_logs, encoding="utf-8")
    (task_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    diff_lines = list(difflib.unified_diff(
        initial_code.splitlines(keepends=True),
        agent_code.splitlines(keepends=True),
        fromfile="starting/main.c",
        tofile="agent/main.c",
    ))
    diff_text = "".join(diff_lines)
    (task_dir / "agent_patches.diff").write_text(diff_text, encoding="utf-8")
    (task_dir / "final_diff.diff").write_text(diff_text, encoding="utf-8")
    return task_dir


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
        if p.name in {"results.json", "latest-summary.json", "failure-breakdown.json"}:
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

    parser = argparse.ArgumentParser(description="STM32F103 Agent vs Plain LLM Benchmark Harness")
    parser.add_argument("--mode", default="compare", choices=["compare", "single"], help="Evaluation mode (default: compare)")
    parser.add_argument("--smoke", action="store_true", help="Run rapid smoke evaluation on 3-5 curated tasks")
    parser.add_argument("--resume", metavar="RUN_ID", help="Resume an interrupted benchmark run by run ID")
    parser.add_argument("--runs-per-task", type=int, default=RUNS_PER_TASK, help="Repetitions per task (default: 1)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of tasks to run")
    args, unknown = parser.parse_known_args()

    limit_raw = args.limit or os.environ.get("BENCH_LIMIT")
    all_tasks = load_tasks()

    if args.smoke:
        smoke_ids = {"1", "4", "8", "20", "39"}
        curated = [t for t in all_tasks if str(t.get("id")) in smoke_ids]
        tasks = curated if len(curated) >= 3 else all_tasks[:5]
    elif limit_raw:
        tasks = all_tasks[: int(limit_raw)]
    else:
        tasks = all_tasks

    model = os.environ.get("LLM_MODEL") or settings.llm_model or ""
    base_url = settings.llm_base_url

    # Checkpoint and directory resolution
    resume_checkpoint = None
    completed_task_ids = set()
    if args.resume:
        run_candidates = [
            RESULTS_BASE / f"run-{args.resume}",
            RESULTS_BASE / args.resume,
        ]
        for rc in run_candidates:
            if (rc / "checkpoint.json").is_file():
                run_dir = rc
                try:
                    resume_checkpoint = json.loads((rc / "checkpoint.json").read_text(encoding="utf-8"))
                    completed_task_ids = set(str(tid) for tid in resume_checkpoint.get("completed_task_ids", []))
                except Exception:
                    pass
                break
        else:
            run_dir = RESULTS_BASE / f"run-{args.resume}"
            run_dir.mkdir(parents=True, exist_ok=True)
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        run_dir = RESULTS_BASE / f"run-{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

    env_meta = collect_environment_metadata(model, base_url)
    env_meta["taskHash"] = compute_task_hash(tasks)
    env_meta["projectHash"] = compute_project_hash()
    env_meta["runsPerTask"] = args.runs_per_task

    summary_path = TASK_DIR / "latest-summary.json"
    comparison_path = ROOT / "benchmarks" / "comparison-summary.json"
    taxonomy_path = TASK_DIR / "failure-breakdown.json"

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
        write_json(run_dir / "config.json", {"limit": limit_raw, "tasks": len(tasks), "model": model, "smoke": args.smoke})
        write_json(run_dir / "environment.json", env_meta)
        write_json(run_dir / "summary.json", summ)
        write_json(run_dir / "comparison.json", comp)

        breakdown = {cat: 0 for cat in FAILURE_TAXONOMY}
        write_json(run_dir / "failure-breakdown.json", breakdown)
        write_json(taxonomy_path, breakdown)

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

    # Resume previous state if available
    if resume_checkpoint:
        baseline_runs = list(resume_checkpoint.get("baseline_runs", []))
        agent_runs = list(resume_checkpoint.get("agent_runs", []))
        failures = list(resume_checkpoint.get("failures", []))
        for r in agent_runs:
            iterations.append(r.get("iterations", 1))
            latencies.append(r.get("seconds", 0.0))
            in_tokens += r.get("input_tokens", 0)
            out_tokens += r.get("output_tokens", 0)
            if r.get("success"):
                agent_compile += 1
            if r.get("semantic_ok"):
                agent_valid += 1
        for br in baseline_runs:
            baseline_tokens += br.get("tokens", 0)
            baseline_latencies.append(br.get("latency", 0.0))
            if br.get("compile_success"):
                baseline_compile += 1
            if br.get("semantic_success"):
                baseline_valid += 1

    out = {
        "schema_version": 2,
        "status": "RUNNING",
        "gcc": True,
        "llm": True,
        "model": model,
        "tasks": list(agent_runs),
        "first_build_success": sum(1 for r in agent_runs if r.get("first_build_ok")),
        "auto_fix_success": sum(1 for r in agent_runs if r.get("success") and not r.get("first_build_ok")),
        "compile_success": agent_compile,
        "semantic_success": agent_valid,
        "avg_iterations": sum(iterations) / max(len(iterations), 1) if iterations else 0.0,
        "skipped": [],
        "environment": env_meta,
        "evidence": [],
    }

    template_main = ROOT / "templates" / "stm32f103_hal_official" / "Core" / "Src" / "main.c"
    initial_main_code = template_main.read_text(encoding="utf-8") if template_main.is_file() else ""

    for task in tasks:
        tid = task.get("id", "bench")
        if str(tid) in completed_task_ids:
            print(f"RESUME: skipping already completed task {tid}")
            continue

        prompt = task["prompt"]

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

        b_main_file = broot / "Core" / "Src" / "main.c"
        baseline_code = b_main_file.read_text(encoding="utf-8") if b_main_file.is_file() else ""

        b_failure_cat = None
        if not b_ok or not b_sem:
            b_failure_cat = classify_failure(
                error=bw.get("error"),
                compiler_logs=b_build.get("combined", "") or b_build.get("error", ""),
                exit_code=b_build.get("exit_code"),
                validation_score=1.0 if b_sem else 0.0,
            )

        baseline_runs.append({
            "id": tid,
            "compile_success": b_ok,
            "semantic_success": b_sem,
            "latency": b_sec,
            "tokens": b_tok,
            "error": b_build.get("error"),
            "failure_category": b_failure_cat,
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

        agent_main_file = root / "Core" / "Src" / "main.c"
        agent_code = agent_main_file.read_text(encoding="utf-8") if agent_main_file.is_file() else ""

        agent_failure_cat = None
        if not last_ok or not sem:
            compile_events = [e for e in run.events if e.get("type") == "compile"]
            last_compile_output = compile_events[-1].get("output", "") if compile_events else ""
            agent_failure_cat = classify_failure(
                compiler_logs=last_compile_output,
                exit_code=0 if last_ok else 1,
                validation_score=1.0 if sem else 0.0,
                iterations=run.iteration,
                max_iterations=settings.max_agent_iterations,
            )

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
            "failure_category": agent_failure_cat,
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

        # Save per-task diff evidence
        save_task_evidence(
            run_dir=run_dir,
            tid=str(tid),
            prompt=prompt,
            starting_project_meta=meta,
            baseline_code=baseline_code,
            agent_code=agent_code,
            initial_code=initial_main_code,
            compiler_logs=b_build.get("combined", "") or b_build.get("error", ""),
            validator_logs=f"semantic_ok={sem}",
            metrics=item,
        )

        # Update benchmark checkpoint after every completed task
        completed_task_ids.add(str(tid))
        checkpoint_data = {
            "completed_task_ids": list(completed_task_ids),
            "last_completed_task": tid,
            "baseline_runs": baseline_runs,
            "agent_runs": agent_runs,
            "failures": failures,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        write_json(run_dir / "checkpoint.json", checkpoint_data)

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

    # Persist structured benchmark run artifacts and failure taxonomy
    breakdown = {cat: 0 for cat in FAILURE_TAXONOMY}
    for f in failures:
        cat = f.get("failure_category", "COMPILE_ERROR")
        breakdown[cat] = breakdown.get(cat, 0) + 1
    write_json(run_dir / "failure-breakdown.json", breakdown)
    write_json(taxonomy_path, breakdown)

    write_json(run_dir / "config.json", {"limit": limit_raw, "tasks": len(tasks), "model": model, "smoke": args.smoke})
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

#!/usr/bin/env python3
"""Behaviour-graded arena for STM32F103.

Every arm solves the same tasks from a fresh copy of the official template and is
graded identically: clean build -> static validation -> Renode simulation of the
behaviour the task asks for (LED timing, UART output). "Compiles" is not a pass.

Arms
  reference  hand-written solutions (proves each task is satisfiable by the grader)
  template   untouched template (negative control: must fail)
  baseline   plain LLM writes main.c, no tools          (needs LLM_* in .env)
  agent      C-Embedded Agent with tools + simulation   (needs LLM_* in .env)
  claude / codex / gemini   local coding CLIs editing the project themselves

Usage
  python benchmarks/sim_arena.py --arms reference,template
  python benchmarks/sim_arena.py --arms claude,codex,gemini --tasks S1,S2
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = Path(__file__).resolve().parent / "stm32f103_sim"
TEMPLATE = ROOT / "templates" / "stm32f103_hal_official"
RESULTS_BASE = ROOT / "benchmark-results"
CLI_TIMEOUT_SEC = int(os.environ.get("ARENA_CLI_TIMEOUT", "900"))
BUILD_ARTIFACTS = ("*.o", "*.d", "*.elf", "*.hex", "*.bin", "*.map", "build")

sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)

from app.sim.renode import checks_from_spec, simulate  # noqa: E402
from app.tools.toolchain import prepend_toolchain_path  # noqa: E402

# Renode's test runner binds a fixed port range; grade one project at a time.
_GRADE_LOCK = threading.Lock()

CLI_PROMPT = (
    "你在一个 STM32F103C8T6 Blue Pill 的 STM32CubeF1 HAL 工程目录里（Makefile + arm-none-eabi-gcc）。\n"
    "任务：{prompt}\n"
    "要求：只修改 Core/Src 和 Core/Inc 下的文件；完成后在当前目录运行 make 确认编译通过"
    "（arm-none-eabi-gcc 和 make 已在 PATH 中）。不要提问，直接完成。"
)


def load_tasks(selected: set[str] | None) -> list[dict[str, Any]]:
    tasks = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(TASK_DIR.glob("S*.json"))]
    return [t for t in tasks if not selected or t["id"] in selected]


def fresh_project(dest: Path) -> Path:
    shutil.copytree(TEMPLATE, dest, ignore=shutil.ignore_patterns(*BUILD_ARTIFACTS))
    return dest


# ---------------------------------------------------------------- grading


def grade(project: Path, task: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    from app.validation import validate_project

    prepend_toolchain_path()
    make = shutil.which("make")
    grade_dir = out_dir / "grade"
    grade_dir.mkdir(parents=True, exist_ok=True)
    if not make or not shutil.which("arm-none-eabi-gcc"):
        return {"passed": False, "build": "UNAVAILABLE", "simulation": "UNAVAILABLE", "reason": "toolchain missing"}

    subprocess.run([make, "clean"], cwd=project, capture_output=True, check=False)
    build = subprocess.run([make, "-j4"], cwd=project, capture_output=True, text=True, check=False, timeout=300)
    (grade_dir / "build.log").write_text((build.stdout or "") + "\n" + (build.stderr or ""), encoding="utf-8")
    built = build.returncode == 0 and (project / "firmware.elf").is_file()

    static = validate_project(project, task["prompt"])
    static_ok = bool(static.get("passed")) or float(static.get("score") or 0) >= 0.8

    sim: dict[str, Any] = {"status": "SKIPPED", "checks": [], "reason": "build failed"}
    if built:
        with _GRADE_LOCK:
            result = simulate(project / "firmware.elf", checks_from_spec(task["oracle"]["behavior"]), results_dir=grade_dir / "renode")
        sim = result.to_dict()
    return {
        "passed": built and sim["status"] == "PASS",
        "build": "PASS" if built else "FAIL",
        "static": "PASS" if static_ok else "FAIL",
        "simulation": sim["status"],
        "checks": sim.get("checks", []),
        "reason": sim.get("reason") if built else (build.stderr or build.stdout or "")[-600:],
    }


# ---------------------------------------------------------------- arms


def arm_reference(task: dict[str, Any], project: Path, out_dir: Path) -> dict[str, Any]:
    ref = TASK_DIR / "reference" / task["id"]
    for src in ref.rglob("*"):
        if src.is_file():
            dst = project / src.relative_to(ref)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return {"ok": True}


def arm_template(task: dict[str, Any], project: Path, out_dir: Path) -> dict[str, Any]:
    return {"ok": True}


def _llm_ready() -> bool:
    from app.config.settings import settings

    return bool(settings.llm_api_key and settings.llm_base_url and settings.llm_model)


def arm_baseline(task: dict[str, Any], project: Path, out_dir: Path) -> dict[str, Any]:
    from app.services.llm import LLMError, chat

    async def _go() -> dict[str, Any]:
        return await chat(
            [
                {"role": "system", "content": "你是嵌入式工程师。只输出完整的 Core/Src/main.c（STM32CubeF1 HAL，Blue Pill），不要解释。"},
                {"role": "user", "content": task["prompt"]},
            ],
            temperature=0,
            max_tokens=4096,
        )

    try:
        data = asyncio.run(_go())
    except LLMError as e:
        return {"ok": False, "error": str(e)}
    text = data["choices"][0]["message"].get("content") or ""
    if "```" in text:
        text = text.split("```")[1]
        text = text[1:] if text[:1] in {"c", "C"} else text
    (project / "Core" / "Src" / "main.c").write_text(text.strip() + "\n", encoding="utf-8")
    usage = data.get("usage") or {}
    return {"ok": True, "tokens": int(usage.get("prompt_tokens") or 0) + int(usage.get("completion_tokens") or 0)}


def arm_agent(task: dict[str, Any], project: Path, out_dir: Path) -> dict[str, Any]:
    from app.agent import runtime
    from app.workspace import manager

    project_id = project.name
    original = manager.project_root
    runtime.project_root = lambda pid: project if pid == project_id else original(pid)
    run = runtime.AgentRun(f"arena-{uuid.uuid4().hex[:8]}", project_id, task["prompt"], "auto")
    try:
        asyncio.run(runtime.run_agent(run))
    finally:
        runtime.project_root = original
    (out_dir / "events.json").write_text(json.dumps(run.events, ensure_ascii=False, indent=1), encoding="utf-8")
    return {
        "ok": run.status == "success",
        "status": run.status,
        "iterations": run.iteration,
        "tokens": run.input_tokens + run.output_tokens,
        "simulated": run.last_simulation is not None,
    }


def _cli(argv: list[str]) -> Callable[[dict[str, Any], Path, Path], dict[str, Any]]:
    def run(task: dict[str, Any], project: Path, out_dir: Path) -> dict[str, Any]:
        exe = shutil.which(argv[0])
        if not exe:
            return {"ok": False, "error": f"{argv[0]} not on PATH"}
        prepend_toolchain_path()
        prompt = CLI_PROMPT.format(prompt=task["prompt"])
        try:
            proc = subprocess.run(
                [exe, *argv[1:]],
                cwd=project,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=CLI_TIMEOUT_SEC,
                check=False,
            )
            output, code = (proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""), proc.returncode
        except subprocess.TimeoutExpired as e:
            output, code = f"TIMEOUT after {CLI_TIMEOUT_SEC}s\n{e.stdout or ''}", -1
        (out_dir / "cli-output.txt").write_text(output, encoding="utf-8")
        info: dict[str, Any] = {"ok": code == 0, "exit_code": code}
        try:  # claude --output-format json
            data = json.loads(proc.stdout)
            info["cost_usd"] = data.get("total_cost_usd")
            info["model"] = next(iter(data.get("modelUsage") or {}), None)
            if data.get("is_error"):
                info["ok"] = False
                info["error"] = str(data.get("result"))[:300]
        except Exception:
            pass
        # A CLI that never got a model response (auth, quota, crash) is an infrastructure
        # error, not a failed solution: it is reported but excluded from the score.
        lowered = output.lower()
        if not info["ok"] and (
            code != 0 or any(k in lowered for k in ("authenticat", "401", "unauthorized", "ineligible", "quota"))
        ):
            info["infra_error"] = True
            info.setdefault("error", output.strip().splitlines()[-1][:300] if output.strip() else "no output")
        return info

    return run


ARMS: dict[str, Callable[[dict[str, Any], Path, Path], dict[str, Any]]] = {
    "reference": arm_reference,
    "template": arm_template,
    "baseline": arm_baseline,
    "agent": arm_agent,
    "claude": _cli(["claude", "-p", "--output-format", "json", "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", "Bash(make:*)"]),
    "codex": _cli(["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", "-"]),
    "gemini": _cli(["gemini", "-p", " ", "--approval-mode", "auto_edit", "--allowed-tools", "run_shell_command(make)", "-o", "json"]),
}


# ---------------------------------------------------------------- driver


def run_arm(arm: str, tasks: list[dict[str, Any]], run_dir: Path, work_root: Path) -> list[dict[str, Any]]:
    rows = []
    for task in tasks:
        out_dir = run_dir / arm / task["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        project = fresh_project(work_root / arm / f"{arm}-{task['id']}-{uuid.uuid4().hex[:6]}")
        t0 = time.perf_counter()
        try:
            solve = ARMS[arm](task, project, out_dir)
        except Exception as e:  # noqa: BLE001 - one arm crashing must not stop the arena
            solve = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        solve_sec = round(time.perf_counter() - t0, 1)
        result = grade(project, task, out_dir)
        row = {"arm": arm, "task": task["id"], "solve_seconds": solve_sec, "solve": solve, **result,
               "infra_error": bool(solve.get("infra_error"))}
        (out_dir / "result.json").write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        for rel in ("Core/Src/main.c", "Core/Src/syscalls.c"):
            if (project / rel).is_file():
                shutil.copy2(project / rel, out_dir / rel.replace("/", "_"))
        verdict = "INFRA-ERROR" if row["infra_error"] else ("PASS" if row["passed"] else "FAIL")
        print(f"[{arm}] {task['id']}: {verdict} "
              f"(build={row['build']} static={row.get('static')} sim={row['simulation']}, {solve_sec}s)", flush=True)
        rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]], tasks: list[dict[str, Any]], arms: list[str]) -> str:
    ids = [t["id"] for t in tasks]
    lines = ["| Arm | " + " | ".join(ids) + " | Build | Static | **Behaviour (sim)** |", "|---" * (len(ids) + 4) + "|"]
    for arm in arms:
        every = {r["task"]: r for r in rows if r["arm"] == arm}
        mine = {tid: r for tid, r in every.items() if not r.get("infra_error")}
        cells = []
        for tid in ids:
            r = every.get(tid)
            if not r:
                cells.append("—")
            elif r.get("infra_error"):
                cells.append("⚠️")
            else:
                cells.append("✅" if r["passed"] else ("🟡" if r["build"] == "PASS" else "❌"))
        if not mine:
            lines.append(f"| {arm} | " + " | ".join(cells) + " | — | — | **not scored (arm errors)** |")
            continue
        n = len(mine)
        build = sum(r["build"] == "PASS" for r in mine.values())
        static = sum(r.get("static") == "PASS" for r in mine.values())
        passed = sum(r["passed"] for r in mine.values())
        lines.append(f"| {arm} | " + " | ".join(cells) + f" | {build}/{n} | {static}/{n} | **{passed}/{n}** |")
    lines.append("")
    lines.append("✅ behaviour verified in Renode · 🟡 compiles but behaviour wrong/unverified · ❌ does not compile"
                 " · ⚠️ arm could not run (auth/quota/crash), excluded from score")
    return "\n".join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arms", default="reference,template")
    parser.add_argument("--tasks", default="")
    parser.add_argument("--parallel", action="store_true", help="solve arms concurrently (grading stays serial)")
    parser.add_argument("--summarize", type=Path, help="re-render summary.md from an existing run directory")
    args = parser.parse_args()
    if args.summarize:
        rows = json.loads((args.summarize / "results.json").read_text(encoding="utf-8"))
        arms_seen = list(dict.fromkeys(r["arm"] for r in rows))
        table = summarize(rows, load_tasks({r["task"] for r in rows}), arms_seen)
        (args.summarize / "summary.md").write_text(table + "\n", encoding="utf-8")
        print(table)
        return 0

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        parser.error(f"unknown arms: {unknown}")
    if any(a in {"baseline", "agent"} for a in arms) and not _llm_ready():
        print("SKIP baseline/agent: LLM_BASE_URL / LLM_API_KEY / LLM_MODEL not configured in .env")
        arms = [a for a in arms if a not in {"baseline", "agent"}]
    tasks = load_tasks({t.strip() for t in args.tasks.split(",") if t.strip()} or None)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RESULTS_BASE / f"sim-arena-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    # Solve outside the repo so CLIs do not pick up this repository's AGENTS.md / CLAUDE.md.
    work_root = Path(tempfile.gettempdir()) / "cea-arena" / stamp

    rows: list[dict[str, Any]] = []
    if args.parallel:
        with ThreadPoolExecutor(max_workers=len(arms)) as pool:
            for part in pool.map(lambda a: run_arm(a, tasks, run_dir, work_root), arms):
                rows.extend(part)
    else:
        for arm in arms:
            rows.extend(run_arm(arm, tasks, run_dir, work_root))

    table = summarize(rows, tasks, arms)
    (run_dir / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "summary.md").write_text(table + "\n", encoding="utf-8")
    print("\n" + table)
    print(f"\nresults: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

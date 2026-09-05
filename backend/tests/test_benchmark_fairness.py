from __future__ import annotations

import asyncio
import json
from pathlib import Path

import benchmarks.benchmark as benchmark
from app.services import llm


def test_agent_arm_pins_deterministic_generation_options(monkeypatch) -> None:
    captured = {}

    async def fake_chat(messages, tools=None, **kwargs):
        captured.update({"messages": messages, "tools": tools, **kwargs})
        return {"choices": []}

    monkeypatch.setattr(llm, "chat", fake_chat)
    asyncio.run(benchmark.agent_chat([{"role": "user", "content": "task"}], [{"type": "function"}]))

    assert captured["temperature"] == 0
    assert captured["max_tokens"] == benchmark.OUTPUT_BUDGET


def test_baseline_arm_pins_the_same_generation_options(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    async def fake_chat(messages, tools=None, **kwargs):
        captured.update({"messages": messages, "tools": tools, **kwargs})
        return {
            "choices": [{"message": {"content": "int main(void) { return 0; }"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 7},
        }

    monkeypatch.setattr(llm, "chat", fake_chat)
    source_dir = tmp_path / "Core" / "Src"
    source_dir.mkdir(parents=True)

    result = benchmark.baseline_write(tmp_path, "task")

    assert result["ok"] is True
    assert captured["temperature"] == 0
    assert captured["max_tokens"] == benchmark.OUTPUT_BUDGET


def test_missing_requirements_are_skipped_without_zero_percentages(monkeypatch, tmp_path: Path) -> None:
    task_dir = tmp_path / "stm32f103"
    task_dir.mkdir()
    (tmp_path / "benchmarks").mkdir()
    monkeypatch.setattr(benchmark, "TASK_DIR", task_dir)
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    monkeypatch.setattr(benchmark, "gcc_ok", lambda: False)
    monkeypatch.setattr(benchmark, "llm_ok", lambda: False)
    monkeypatch.setattr(benchmark, "load_tasks", lambda: [])

    assert benchmark.main() == 0

    summary = json.loads((task_dir / "latest-summary.json").read_text(encoding="utf-8"))
    comparison = json.loads((tmp_path / "benchmarks" / "comparison-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SKIPPED"
    assert summary["skipped"] == ["arm-none-eabi-gcc or make missing", "LLM not configured"]
    assert summary["finalCompileSuccess"] is None
    assert comparison["baselineCompileSuccess"] is None
    assert comparison["agentCompileSuccess"] is None


def test_reproducible_metadata_contains_required_fields() -> None:
    meta = benchmark.collect_environment_metadata("test-model", "https://api.openai.com/v1")
    assert "gitCommitSha" in meta
    assert "os" in meta
    assert "python" in meta
    assert meta["model"] == "test-model"
    assert meta["baseUrlHost"] == "api.openai.com"
    # Never leak API key or full URL with credentials
    assert "apiKey" not in meta
    assert "test-key" not in str(meta)


def test_benchmark_failure_taxonomy() -> None:
    # 1. LLM / Timeout
    assert benchmark.classify_failure(error="Request timed out") == "TIMEOUT"
    assert benchmark.classify_failure(error="API rate limit exceeded") == "LLM_GENERATION_ERROR"
    assert benchmark.classify_failure(error="Hardware disconnected") == "HARDWARE_UNAVAILABLE"

    # 2. Compile / Link errors
    assert benchmark.classify_failure(compiler_logs="undefined reference to HAL_GPIO_Init", exit_code=1) == "LINK_ERROR"
    assert benchmark.classify_failure(compiler_logs="syntax error before token", exit_code=1) == "SYNTAX_ERROR"
    assert benchmark.classify_failure(compiler_logs="fatal error: stm32f1xx_hal.h: No such file", exit_code=1) == "COMPILE_ERROR"

    # 3. Agent loop limit & validation
    assert benchmark.classify_failure(iterations=10, max_iterations=10) == "AGENT_LOOP_LIMIT"
    assert benchmark.classify_failure(validation_score=0.5) == "STATIC_VALIDATION_ERROR"


def test_benchmark_diff_evidence_saving(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-test-ev"
    task_dir = benchmark.save_task_evidence(
        run_dir=run_dir,
        tid="01",
        prompt="Configure LED PC13",
        starting_project_meta={"id": "proj-1", "mcu": "STM32F103C8T6"},
        baseline_code="/* baseline code */",
        agent_code="/* agent code with LED */",
        initial_code="/* starting code */",
        compiler_logs="Build OK",
        validator_logs="Score 1.0",
        metrics={"status": "PASS", "seconds": 3.2},
    )
    assert task_dir.is_dir()
    assert (task_dir / "prompt.txt").read_text(encoding="utf-8") == "Configure LED PC13"
    assert (task_dir / "starting_project.json").is_file()
    assert (task_dir / "baseline_output.c").is_file()
    assert (task_dir / "agent_output.c").is_file()
    assert (task_dir / "agent_patches.diff").is_file()
    assert (task_dir / "final_diff.diff").is_file()
    assert (task_dir / "metrics.json").is_file()
    diff_content = (task_dir / "agent_patches.diff").read_text(encoding="utf-8")
    assert "+/* agent code with LED */" in diff_content


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

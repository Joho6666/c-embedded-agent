from __future__ import annotations

import json
from pathlib import Path

from app.agent.checkpoint import RunCheckpoint, get_checkpoint_path, load_run_checkpoint, save_run_checkpoint
from app.agent.runtime import AgentRun, restore_run_from_checkpoint


def test_checkpoint_save_and_load_disk(tmp_path: Path) -> None:
    cp = RunCheckpoint(
        run_id="run-chk-001",
        project_id="test-proj",
        prompt="Blink LED at PC13",
        mode="auto",
        status="running",
        phase="reasoning",
        iteration=2,
        messages=[{"role": "user", "content": "hello"}, {"role": "assistant", "content": "reading files"}],
        last_errors=[{"message": "syntax error", "line": 42}],
        snapshot_sha="sha123456",
        serial_device="COM3",
        expect="CEA:PASS",
    )
    saved_path = save_run_checkpoint(cp, repo_root=tmp_path)
    assert saved_path.is_file()
    assert (tmp_path / "runs" / "run-chk-001" / "checkpoint.json").is_file()

    loaded = load_run_checkpoint("run-chk-001", repo_root=tmp_path)
    assert loaded is not None
    assert loaded.run_id == "run-chk-001"
    assert loaded.project_id == "test-proj"
    assert loaded.iteration == 2
    assert loaded.phase == "reasoning"
    assert len(loaded.messages) == 2
    assert loaded.last_errors[0]["line"] == 42
    assert loaded.snapshot_sha == "sha123456"
    assert loaded.serial_device == "COM3"


def test_restore_run_from_checkpoint() -> None:
    cp = RunCheckpoint(
        run_id="run-chk-002",
        project_id="p1",
        prompt="PWM generator",
        mode="advanced",
        status="running",
        phase="plan",
        iteration=1,
        action_plan={"steps": [{"index": 1, "title": "configure timer"}]},
        serial_baud=115200,
    )
    run = restore_run_from_checkpoint(cp)
    assert isinstance(run, AgentRun)
    assert run.id == "run-chk-002"
    assert run.project_id == "p1"
    assert run.prompt == "PWM generator"
    assert run.mode == "advanced"
    assert run.phase == "plan"
    assert run.iteration == 1
    assert run.action_plan == {"steps": [{"index": 1, "title": "configure timer"}]}


def test_missing_checkpoint_returns_none(tmp_path: Path) -> None:
    assert load_run_checkpoint("non-existent-run", repo_root=tmp_path) is None

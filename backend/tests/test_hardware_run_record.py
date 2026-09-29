"""Phase D tests: HardwareRun persistence from the pipeline, checkpoints, diagnose API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.hardware import session as hwrun
from app.hardware.checkpoint import StageCheckpoint
from app.tools.hardware_run import run_pipeline
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------- checkpoint

def test_checkpoint_pending_and_resume(tmp_path: Path):
    path = tmp_path / "hardware-runs" / "checkpoint-hw-1.json"
    cp = StageCheckpoint("hw-1", ["build", "flash", "reset", "serial", "validate"], path=path)
    assert cp.pending_stages() == ["build", "flash", "reset", "serial", "validate"]
    cp.mark_done("build", {"status": "SUCCESS"})
    cp.mark_done("flash", {"status": "SUCCESS"})
    assert cp.pending_stages() == ["reset", "serial", "validate"]
    # new instance (crash recovery) sees the same state
    cp2 = StageCheckpoint("hw-1", ["build", "flash", "reset", "serial", "validate"], path=path)
    assert cp2.completed_stages() == ["build", "flash"]
    assert cp2.summary_of("build") == {"status": "SUCCESS"}
    cp2.finish("PASS")
    assert StageCheckpoint("hw-1", ["build", "flash", "reset"], path=path)._data["status"] == "PASS"


def test_checkpoint_rejects_unknown_stage_and_empty(tmp_path: Path):
    cp = StageCheckpoint("hw-2", ["build"], path=tmp_path / "cp.json")
    with pytest.raises(ValueError):
        cp.mark_done("teleport")
    with pytest.raises(ValueError):
        StageCheckpoint("hw-3", [], path=tmp_path / "cp2.json")


def test_checkpoint_reset(tmp_path: Path):
    cp = StageCheckpoint("hw-4", ["build", "flash"], path=tmp_path / "cp3.json")
    cp.mark_done("build")
    cp.reset()
    assert cp.pending_stages() == ["build", "flash"]


# ---------------------------------------------------------------- run records

@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "Core" / "Src").mkdir(parents=True)
    (root / "Makefile").write_text("TARGET = firmware\n", encoding="utf-8")
    return root


def test_pipeline_build_failure_records_fail_run(project: Path, monkeypatch):
    from app.tools.compiler import CompileError

    monkeypatch.setattr("app.tools.hardware_run.compile_project", lambda r: (_ for _ in ()).throw(CompileError("boom")))
    result = run_pipeline(project, task="led")
    assert result["runId"] and result["runId"].startswith("hw-")
    runs = hwrun.load_runs(project)
    assert len(runs) == 1
    assert runs[0]["status"] == "FAIL"
    assert runs[0]["finishedAt"]


def test_pipeline_no_probe_records_unavailable(project: Path, monkeypatch):
    monkeypatch.setattr(
        "app.tools.hardware_run.compile_project",
        lambda r: {"success": True, "combined": "ok", "memory": {"text": 2800, "data": 20}},
    )
    monkeypatch.setattr("app.tools.hardware_run.detect_chip_id", lambda: {"available": False})
    result = run_pipeline(project, task="led")
    assert result["validation"]["status"] == "UNAVAILABLE"
    runs = hwrun.load_runs(project)
    assert runs[0]["status"] == "UNAVAILABLE"
    assert runs[0]["flashResult"] is None
    assert runs[0]["serialLog"] == []


def test_pipeline_pass_records_full_evidence(project: Path, monkeypatch):
    (project / "firmware.bin").write_bytes(b"fw-bytes")
    monkeypatch.setattr(
        "app.tools.hardware_run.compile_project",
        lambda r: {"success": True, "combined": "ok", "memory": {"text": 3600, "data": 20}},
    )
    monkeypatch.setattr(
        "app.tools.hardware_run.detect_chip_id",
        lambda: {"available": True, "family": "STM32F1", "output": "0x1ba01477"},
    )
    monkeypatch.setattr(
        "app.tools.hardware_run.flash_elf",
        lambda r: {"success": True, "exit_code": 0, "output": "verified"},
    )
    monkeypatch.setattr("app.tools.hardware_run.serial_connect", lambda d, b: {"ok": True})
    monkeypatch.setattr(
        "app.tools.hardware_run.serial_wait_for",
        lambda expect=None, max_s=8.0, quiet=0.3: ["boot", "CEA:USART:PASS"],
    )
    result = run_pipeline(project, serial_device="COM7", expect="CEA:USART:PASS", task="usart")
    assert result["validation"]["status"] == "PASS"
    runs = hwrun.load_runs(project)
    rec = runs[0]
    assert rec["status"] == "PASS"  # gate satisfied: flash success + hardware evidence
    assert rec["flashResult"]["success"] is True
    assert any("CEA:USART:PASS" in ln for ln in rec["serialLog"])
    assert any(e["level"] == "HARDWARE" and e["passed"] for e in rec["hardwareEvidence"])
    assert rec["firmwareHash"] is not None


def test_run_record_rejects_fake_pass(project: Path, monkeypatch):
    """flash success alone must not finalize PASS — pipeline downgrades to PARTIAL."""
    monkeypatch.setattr(
        "app.tools.hardware_run.compile_project",
        lambda r: {"success": True, "combined": "ok", "memory": {}},
    )
    monkeypatch.setattr(
        "app.tools.hardware_run.detect_chip_id",
        lambda: {"available": True, "family": "STM32F1", "output": "0x1ba01477"},
    )
    monkeypatch.setattr(
        "app.tools.hardware_run.flash_elf",
        lambda r: {"success": True, "exit_code": 0, "output": "verified"},
    )
    monkeypatch.setattr("app.tools.hardware_run.serial_connect", lambda d, b: {"ok": True})
    monkeypatch.setattr("app.tools.hardware_run.serial_wait_for", lambda expect=None, max_s=8.0, quiet=0.3: [])
    result = run_pipeline(project, serial_device="COM7", task="usart")
    # hardware_status cannot PASS without the serial token
    assert result["validation"]["status"] != "PASS"
    rec = hwrun.load_runs(project)[0]
    assert rec["status"] in {"PARTIAL", "FAIL", "UNKNOWN", "UNAVAILABLE"}


# ---------------------------------------------------------------- debugger API

def test_diagnose_endpoint_project_missing():
    r = client.post("/api/hardware/debugger/diagnose", json={"projectId": "no-such-project"})
    assert r.status_code == 404


def test_diagnose_endpoint_honest_without_hardware(project: Path):
    from app.workspace.manager import project_root as real_project_root
    from app.workspace import manager

    # register a fake project dir for the endpoint lookup
    orig = manager.project_root
    monkey_root = project

    def fake_root(pid: str) -> Path:
        if pid == "diag-proj":
            return monkey_root
        return orig(pid)

    import app.main as main_mod

    main_mod.project_root = fake_root
    try:
        r = client.post("/api/hardware/debugger/diagnose", json={"projectId": "diag-proj", "task": "led"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in {"FAIL", "UNAVAILABLE", "PARTIAL", "UNKNOWN"}
        assert body["steps"][0]["step"] == "build"
        assert body["crashEvidence"] is None or body["crashEvidence"]["kind"] == "CrashEvidence"
    finally:
        main_mod.project_root = orig

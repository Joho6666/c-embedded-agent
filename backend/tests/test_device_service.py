"""DeviceService behaviour with a scripted backend (no simulator or probe needed)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.device.base import DeviceBackend, DeviceError, parse_pin
from app.device.service import DeviceService, resolve_project


class ScriptedBoard(DeviceBackend):
    """Emits a fixed serial script per firmware; ``advance`` delivers it like a virtual board."""

    kind = "virtual"
    evidence = "SIMULATED"

    def __init__(self, scripts: dict[str, list[str]]) -> None:
        super().__init__()
        self.scripts = scripts
        self.firmware: Path | None = None
        self.virtual_time = 0.0
        self.flashes: list[Path] = []

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def open(self) -> None: ...

    def flash(self, elf: Path) -> dict[str, Any]:
        self.firmware = elf
        self.flashes.append(elf)
        return {"ok": True}

    def reset(self) -> dict[str, Any]:
        return {"ok": True}

    def tick(self) -> None: ...

    def advance(self, seconds: float) -> None:
        self.virtual_time += seconds
        for chunk in self.scripts.get(self.firmware.read_text(encoding="utf-8"), []):
            self.emit_serial("usart1", chunk)

    def read_pins(self, pins: list[str]) -> dict[str, dict[str, Any]]:
        return {pin: {"output": True, "input": True} for pin in pins}


def _project(tmp_path: Path, name: str, firmware_id: str) -> Path:
    root = tmp_path / name
    root.mkdir()
    (root / "Makefile").write_text("all:\n", encoding="utf-8")
    (root / "firmware.elf").write_text(firmware_id, encoding="utf-8")
    return root


@pytest.fixture
def service(monkeypatch) -> DeviceService:
    board = ScriptedBoard({"hello-fw": ["Hel", "lo\r", "\nBoot OK\r\n"], "quiet-fw": []})
    svc = DeviceService(board, pace_interval_s=0.01)

    def fake_build(project: str | None = None) -> dict[str, Any]:
        root = resolve_project(project)
        ok = (root / "firmware.elf").read_text(encoding="utf-8") != "broken"
        svc.last_build = {"success": ok}
        return {"success": ok, "errors": [] if ok else [{"message": "boom"}], "memory": None, "warnings": 0, "seconds": 0.1}

    monkeypatch.setattr(svc, "build", fake_build)
    yield svc
    svc.close()


def test_serial_lines_survive_crlf_split_across_chunks(service: DeviceService, tmp_path: Path) -> None:
    result = service.flash(str(_project(tmp_path, "a", "hello-fw")), expect="Boot OK", observe_s=0.5)
    assert result["success"] and result["expect_found"] is True
    assert result["serial"] == ["Hello", "Boot OK"]
    assert result["evidence"] == "SIMULATED"


def test_missing_expect_fails_and_output_is_scoped_to_current_firmware(service: DeviceService, tmp_path: Path) -> None:
    service.flash(str(_project(tmp_path, "a", "hello-fw")), observe_s=0.5)
    result = service.flash(str(_project(tmp_path, "b", "quiet-fw")), expect="Hello", observe_s=0.5)
    assert result["success"] is False and result["stage"] == "observe" and result["serial"] == []
    assert service.serial_tail()["lines"] == []
    assert len(service.serial_tail(current_firmware_only=False)["lines"]) == 2
    assert service.last_flash["expect_found"] is False


def test_build_failure_never_flashes(service: DeviceService, tmp_path: Path) -> None:
    result = service.flash(str(_project(tmp_path, "c", "broken")), expect="x")
    assert result["success"] is False and result["stage"] == "build"
    assert service.backend.flashes == []


def test_status_reports_latest_state(service: DeviceService, tmp_path: Path) -> None:
    assert "pins" not in service.status()
    service.flash(str(_project(tmp_path, "a", "hello-fw")), observe_s=0.5)
    state = service.status(["PC13"])
    assert state["last_flash"]["success"] and state["last_flash"]["sha256_12"]
    assert state["serial_tail"] == ["Hello", "Boot OK"]
    assert state["pins"]["PC13"]["output"] is True
    assert [e["kind"] for e in state["recent_events"]][-1] == "flash"


def test_project_and_pin_validation(tmp_path: Path) -> None:
    with pytest.raises(DeviceError):
        resolve_project(str(tmp_path))
    assert parse_pin("PC13") == ("C", 13) and parse_pin("a0") == ("A", 0)
    with pytest.raises(ValueError):
        parse_pin("PZ3")


class LateSerialBoard(ScriptedBoard):
    """Delivers serial bytes from another thread after the simulation step returns (loaded host)."""

    def advance(self, seconds: float) -> None:
        import threading
        import time as _time

        def late() -> None:
            _time.sleep(0.4)
            self.emit_serial("usart1", "Hello\r\n")

        threading.Thread(target=late, daemon=True).start()


def test_flash_waits_for_late_serial_bytes(monkeypatch, tmp_path: Path) -> None:
    svc = DeviceService(LateSerialBoard({}), pace_interval_s=0.01)
    monkeypatch.setattr(svc, "build", lambda project=None: {"success": True, "memory": None, "warnings": 0, "seconds": 0})
    try:
        result = svc.flash(str(_project(tmp_path, "late", "fw")), expect="Hello", observe_s=0.1)
        assert result["expect_found"] is True, result["serial"]
    finally:
        svc.close()

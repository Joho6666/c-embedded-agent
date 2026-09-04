from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import (
    build_project,
    check_pin_conflicts,
    diagnose_build,
    flash_firmware,
    get_board_context,
    inspect_project,
    list_serial_ports,
    parse_ioc,
    read_serial,
    validate_hardware,
)
from app.core.security import reset_flash_budget_for_tests
from app.tools.compiler import CompileError
from app.tools.flash import FlashError

REPO = Path(__file__).resolve().parents[2]


def _hal_tree(tmp_path: Path, *, ioc: bool = True) -> Path:
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Drivers" / "STM32F1xx_HAL_Driver" / "Src").mkdir(parents=True)
    (tmp_path / "Core" / "Src" / "main.c").write_text("int main(void){return 0;}\n", encoding="utf-8")
    (tmp_path / "Drivers" / "STM32F1xx_HAL_Driver" / "Src" / "stm32f1xx_hal.c").write_text("void HAL_Init(void){}\n", encoding="utf-8")
    (tmp_path / "startup_stm32f103xb.s").write_text(".syntax unified\n", encoding="utf-8")
    (tmp_path / "STM32F103C8Tx_FLASH.ld").write_text("MEMORY {}\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("all:\n\t@echo skip\n", encoding="utf-8")
    if ioc:
        src = REPO / "templates" / "bluepill.ioc"
        (tmp_path / "board.ioc").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_inspect_project_reads_ioc(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path)
    out = inspect_project(root)
    assert out["status"] == "SUCCESS"
    assert out["side_effect"] == "READ_ONLY"
    assert out["ok"] is True
    assert out["mcu_defaulted"] is False
    assert "STM32F103" in str(out.get("mcu") or "")
    assert out["build_system"] == "make"


def test_inspect_project_marks_defaulted_mcu(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path, ioc=False)
    out = inspect_project(root)
    assert out["status"] == "SUCCESS"
    assert out["mcu_defaulted"] is True
    assert out["mcu_source"] == "default"


def test_inspect_missing_path() -> None:
    out = inspect_project(REPO / "definitely-missing-cea-project")
    assert out["status"] == "FAIL"
    assert "not a directory" in str(out.get("reason") or "")


def test_parse_ioc_bluepill(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path)
    out = parse_ioc(root)
    assert out["status"] == "SUCCESS"
    assert out["mcu"]
    assert out["clocks"]["sysclkHz"] == 72_000_000
    assert any(p.get("pin") == "PA9" for p in out["pins"])
    assert out["usart"]
    assert "interrupts" in out


def test_parse_ioc_missing(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path, ioc=False)
    out = parse_ioc(root)
    assert out["status"] == "UNKNOWN"
    assert out["mcu"] is None
    assert out["usart"] == []


def test_parse_ioc_rejects_escape(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path)
    out = parse_ioc(root, ioc_path="../secret.ioc")
    assert out["status"] in {"UNKNOWN", "FAIL"}
    assert out.get("mcu") in (None, "")


def test_pin_conflicts_unknown_without_evidence(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    out = check_pin_conflicts(empty)
    assert out["status"] == "UNKNOWN"
    assert out["result"] == "UNKNOWN"


def test_pin_conflicts_pass_on_bluepill_ioc(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path)
    out = check_pin_conflicts(root)
    assert out["result"] in {"PASS", "WARNING", "FAIL"}
    assert out["status"] == out["result"]
    assert "evidence" in out


def test_board_context_priority(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path)
    (root / "project.json").write_text(json.dumps({"mcu": "FROM_PROJECT", "board": "FromProject", "led": "PA1"}), encoding="utf-8")
    out = get_board_context(root)
    assert out["status"] == "SUCCESS"
    assert out["sources"]["priority"].startswith("IOC")
    # IOC wins over project.json
    assert "STM32F103" in str(out["mcu"])
    assert out["sources"]["mcu"] == "ioc"
    assert out["led"] == "PC13"


def test_build_toolchain_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _hal_tree(tmp_path)

    def _boom(_root: Path):
        raise CompileError("未检测到 arm-none-eabi-gcc，无法真实编译。")

    monkeypatch.setattr("app.core.build.compile_project", _boom)
    out = build_project(root)
    assert out["status"] == "UNAVAILABLE"
    assert out["success"] is False
    assert "arm-none-eabi-gcc" in str(out.get("reason") or "")


def test_build_make_zero_without_elf_is_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _hal_tree(tmp_path)

    def _fake(_root: Path):
        return {
            "success": True,
            "exit_code": 0,
            "stdout": "skip",
            "stderr": "",
            "combined": "skip",
            "diagnostics": [],
            "artifacts": [],
            "memory": None,
        }

    monkeypatch.setattr("app.core.build.compile_project", _fake)
    out = build_project(root)
    assert out["status"] == "FAIL"
    assert out["success"] is False
    assert "firmware.elf is missing" in str(out.get("reason") or "")


def test_diagnose_without_log(tmp_path: Path) -> None:
    root = _hal_tree(tmp_path)
    out = diagnose_build(root)
    assert out["status"] == "UNKNOWN"
    assert out["side_effect"] == "READ_ONLY"


def test_diagnose_undefined_hal() -> None:
    log = "main.c:12: undefined reference to `HAL_UART_Init'"
    out = diagnose_build(REPO / "templates" / "stm32f103_hal_official", log=log)
    assert out["status"] == "FAIL"
    assert "missing_hal_module" in out["categories"] or any(i.get("category") == "undefined_symbol" for i in out["issues"])
    assert out["error_memory"]


def test_flash_missing_elf(tmp_path: Path) -> None:
    reset_flash_budget_for_tests()
    root = _hal_tree(tmp_path)
    out = flash_firmware(root)
    assert out["status"] == "FAIL"
    assert out["success"] is False
    assert "firmware.elf" in str(out.get("reason") or "")


def test_flash_openocd_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_flash_budget_for_tests()
    root = _hal_tree(tmp_path)
    (root / "firmware.elf").write_bytes(b"\x00")

    def _boom(_root: Path):
        raise FlashError("未检测到 openocd")

    monkeypatch.setattr("app.core.flash.flash_elf", _boom)
    out = flash_firmware(root)
    assert out["status"] == "UNAVAILABLE"
    assert out["success"] is False


def test_serial_ports_shape() -> None:
    out = list_serial_ports()
    assert out["status"] in {"SUCCESS", "UNAVAILABLE"}
    assert isinstance(out.get("ports"), list)
    if out["status"] == "SUCCESS" and out["ports"]:
        assert "port" in out["ports"][0]


def test_read_serial_requires_port() -> None:
    out = read_serial(port="")
    assert out["status"] == "FAIL"
    assert out.get("fabricated") is not True


def test_hardware_unavailable_without_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _hal_tree(tmp_path)

    def _fake_pipeline(_root, **_kwargs):
        return {
            "available": True,
            "steps": [{"kind": "build", "status": "success"}],
            "validation": {"status": "UNAVAILABLE", "reason": "Hardware Not Tested"},
        }

    monkeypatch.setattr("app.core.validation.run_pipeline", _fake_pipeline)
    out = validate_hardware(root, task="usart")
    assert out["status"] == "UNAVAILABLE"
    assert out["hardware_passed"] is False
    assert out["status"] != "PASS"


def test_hardware_never_promotes_compile_to_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _hal_tree(tmp_path)

    def _lie(_root, **_kwargs):
        return {
            "available": True,
            "steps": [{"kind": "build", "status": "success"}],
            "validation": {"status": "PASS", "reason": "should be rejected"},
        }

    monkeypatch.setattr("app.core.validation.run_pipeline", _lie)
    out = validate_hardware(root, serial_device=None, task="led")
    assert out["status"] != "PASS"
    assert out["hardware_passed"] is False


def test_allowed_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = tmp_path / "ok"
    allowed.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("CEA_ALLOWED_ROOTS", str(allowed))
    bad = inspect_project(other)
    assert bad["status"] == "FAIL"
    good = inspect_project(allowed)
    assert good["status"] in {"SUCCESS", "FAIL"}

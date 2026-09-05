from __future__ import annotations

import json
from pathlib import Path

from app.platforms.mcu8051 import adapter as mcu_module
from app.platforms.mcu8051.adapter import Mcu8051SdccAdapter
from app.platforms.registry import default_registry


def adapter() -> Mcu8051SdccAdapter:
    return Mcu8051SdccAdapter(Path(__file__).resolve().parents[2])


def test_8051_template_creation_and_detection(tmp_path: Path) -> None:
    destination = tmp_path / "c51_proj"
    created = adapter().create_template(destination, name="Test 8051 Blink")
    assert created.success
    assert (destination / "project.json").is_file()
    assert (destination / "Makefile").is_file()
    assert (destination / "8051_compat.h").is_file()
    assert (destination / "main.c").is_file()

    project = json.loads((destination / "project.json").read_text(encoding="utf-8"))
    assert project["adapterId"] == "8051-sdcc"
    assert project["platform"] == "8051"
    assert project["mcu"] == "STC89C52RC"

    detection = adapter().detect_project(destination)
    assert detection.matched
    assert detection.confidence >= 0.8


def test_8051_registry_resolution(tmp_path: Path) -> None:
    reg = default_registry(Path(__file__).resolve().parents[2])
    res_id = reg.resolve_explicit(adapter_id="8051-sdcc")
    assert res_id.status == "resolved"
    assert res_id.adapter.adapter_id == "8051-sdcc"

    res_alias = reg.resolve_explicit(platform="8051", mcu="stc89c52")
    assert res_alias.status == "resolved"
    assert res_alias.adapter.adapter_id == "8051-sdcc"


def test_8051_static_validation(tmp_path: Path) -> None:
    inst = adapter()
    (tmp_path / "main.c").write_text(
        '#include "8051_compat.h"\nvoid main() { P1 = 0; while(1) { delay(100); } }\n',
        encoding="utf-8",
    )
    assert inst.validate_static(tmp_path, "Blink LED on P1").success

    (tmp_path / "uart.c").write_text(
        '#include "8051_compat.h"\nvoid init() { TMOD = 0x20; SCON = 0x50; TR1 = 1; SBUF = 0; }\n',
        encoding="utf-8",
    )
    assert inst.validate_static(tmp_path, "Configure UART 9600").success


def test_8051_hardware_no_fake_pass() -> None:
    inst = adapter()
    # Without hardware, must be UNAVAILABLE, never PASS
    val_none = inst.validate_hardware(serial_lines=None, expect=None, task="gpio", has_probe=False)
    assert val_none.status == "UNAVAILABLE"

    # With hardware probe but wrong serial content -> FAIL
    val_fail = inst.validate_hardware(serial_lines=["booting..."], expect="CEA:8051:PASS", task="gpio", has_probe=True)
    assert val_fail.status == "FAIL"

    # With marker -> PASS
    val_pass = inst.validate_hardware(serial_lines=["CEA:8051:PASS"], expect="CEA:8051:PASS", task="gpio", has_probe=True)
    assert val_pass.status == "PASS"


def test_missing_sdcc_returns_unavailable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mcu_module.shutil, "which", lambda _: None)
    inst = adapter()
    build_res = inst.build(tmp_path)
    assert build_res.status == "UNAVAILABLE"
    assert "not installed" in (build_res.reason or "")


def test_8051_golden_projects_present() -> None:
    golden_dir = Path(__file__).resolve().parents[2] / "examples" / "golden_8051"
    projects = [p.name for p in golden_dir.iterdir() if p.is_dir()]
    assert "8051_led" in projects
    assert "8051_timer" in projects
    assert "8051_uart" in projects
    assert "8051_exti" in projects
    for name in ("8051_led", "8051_timer", "8051_uart", "8051_exti"):
        p = golden_dir / name
        assert (p / "Makefile").is_file()
        assert (p / "main.c").is_file()
        assert (p / "8051_compat.h").is_file()
        assert (p / "project.json").is_file()


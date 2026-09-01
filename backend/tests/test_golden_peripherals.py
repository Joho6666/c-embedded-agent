from pathlib import Path

import pytest

from app.config.settings import settings
from app.tools.compiler import compile_project
from app.tools.detect import gcc_installed, make_installed
from app.tools.gcc_parser import parse_gcc_output
from app.workspace.manager import create_project, project_root

pytestmark = pytest.mark.skipif(not gcc_installed() or not make_installed(), reason="ARM GCC or make missing")


def test_gpio_pin_99_then_fix(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    meta = create_project("pin99")
    root = project_root(meta["id"])
    gpio = root / "Core" / "Src" / "gpio.c"
    original = gpio.read_text(encoding="utf-8")
    gpio.write_text(original.replace("LED_Pin", "GPIO_PIN_99", 1), encoding="utf-8")
    bad = compile_project(root)
    assert bad["success"] is False
    diags = bad["diagnostics"] or parse_gcc_output(bad.get("combined", ""))
    blob = " ".join(d.get("message", "") for d in diags) + bad.get("combined", "")
    assert "GPIO_PIN_99" in blob or "undeclared" in blob.lower()
    gpio.write_text(original, encoding="utf-8")
    good = compile_project(root)
    assert good["success"], good.get("combined", "")[-1500:]
    assert (root / "firmware.elf").is_file()


def test_official_template_led_size(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    meta = create_project("led")
    root = project_root(meta["id"])
    result = compile_project(root)
    assert result["success"], result.get("combined", "")[-1500:]
    mem = result.get("memory") or {}
    assert mem.get("flash", 0) > 1000
    assert mem.get("flash", 0) < 64 * 1024

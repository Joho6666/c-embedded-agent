from __future__ import annotations

import json
from pathlib import Path

from app.platforms.stm32f103 import adapter as stm_module
from app.platforms.stm32f103.adapter import Stm32F103Adapter


def adapter() -> Stm32F103Adapter:
    return Stm32F103Adapter(Path(__file__).resolve().parents[2])


def test_context_precedence_ioc_over_project_board_and_defaults(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text(
        json.dumps({"mcu": "project-mcu", "board": "project-board", "clockMHz": 8}), encoding="utf-8"
    )
    (tmp_path / "actual.ioc").write_text(
        "Mcu.Name=STM32F103RBTx\nMcu.Family=STM32F1\nRCC.HCLKFreq_Value=64000000\n",
        encoding="utf-8",
    )
    context = adapter().load_context(tmp_path)
    assert context["facts"]["mcu"] == "STM32F103RBTx"
    assert context["sources"] == ["adapter defaults", "board profile", "project.json", "IOC"]


def test_create_template_adds_adapter_metadata(tmp_path: Path) -> None:
    destination = tmp_path / "project"
    result = adapter().create_template(destination, name="blink", metadata={"adapterId": "wrong", "id": "p1"})
    assert result.success is True
    metadata = json.loads((destination / "project.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "p1"
    assert metadata["adapterId"] == "stm32f103-hal"
    assert "build" in metadata["capabilities"]
    assert (destination / "Makefile").is_file()


def test_build_delegates_to_existing_compiler(monkeypatch, tmp_path: Path) -> None:
    seen = {}

    def fake_compile(root: Path):
        seen["root"] = root
        return {"success": True, "exit_code": 0, "artifacts": [{"name": "firmware.elf"}]}

    monkeypatch.setattr(stm_module, "compile_project", fake_compile)
    result = adapter().build(tmp_path)
    assert result.success is True
    assert seen["root"] == tmp_path
    assert result.evidence == ["firmware.elf"]


def test_generator_and_validator_delegate(monkeypatch, tmp_path: Path) -> None:
    generated = {}
    validated = {}

    def fake_generate(root: Path, kind: str, args: dict):
        generated.update({"root": root, "kind": kind, "args": args})
        return {"ok": True, "files": ["Core/Src/adc.c"]}

    def fake_validate(root: Path, task: str):
        validated.update({"root": root, "task": task})
        return {"passed": True, "kinds": ["adc"]}

    monkeypatch.setattr(stm_module, "configure_peripheral", fake_generate)
    monkeypatch.setattr(stm_module, "validate_project", fake_validate)
    inst = adapter()
    assert inst.generate_peripheral(tmp_path, "adc", {"mode": "dma"}).success
    assert inst.validate_static(tmp_path, "ADC DMA acquisition").success
    assert generated["kind"] == "adc"
    assert validated["task"] == "ADC DMA acquisition"


def test_hardware_pipeline_receives_real_task(monkeypatch, tmp_path: Path) -> None:
    seen = {}
    monkeypatch.setattr(stm_module, "detect_chip_id", lambda: {"available": True, "family": "STM32F1"})

    def fake_pipeline(root: Path, **kwargs):
        seen.update(kwargs)
        return {"validation": {"status": "PASS"}, "steps": []}

    monkeypatch.setattr(stm_module, "run_pipeline", fake_pipeline)
    result = adapter().hardware_run(tmp_path, task="ADC DMA acquisition")
    assert result.success is True
    assert seen["task"] == "ADC DMA acquisition"


def test_device_operations_require_detected_hardware(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(stm_module, "detect_chip_id", lambda: {"available": False, "family": None})
    monkeypatch.setattr(stm_module, "list_ports", lambda: [])
    inst = adapter()
    assert inst.flash(tmp_path).status == "UNAVAILABLE"
    assert inst.hardware_run(tmp_path).status == "UNAVAILABLE"
    assert inst.serial_sample(device="COM99").status == "UNAVAILABLE"

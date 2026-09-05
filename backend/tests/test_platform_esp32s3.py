from __future__ import annotations

import json
from pathlib import Path

from app.platforms.esp32s3 import adapter as esp_module
from app.platforms.esp32s3.adapter import Esp32S3IdfAdapter


def adapter() -> Esp32S3IdfAdapter:
    return Esp32S3IdfAdapter(Path(__file__).resolve().parents[2])


def test_template_is_detectable_and_validates_gpio(tmp_path: Path) -> None:
    destination = tmp_path / "esp"
    created = adapter().create_template(destination, name="esp blink", metadata={"id": "e1"})
    assert created.success
    metadata = json.loads((destination / "project.json").read_text(encoding="utf-8"))
    assert metadata["adapterId"] == "esp32s3-idf"
    assert metadata["mcu"] == "ESP32-S3"
    detection = adapter().detect_project(destination)
    assert detection.matched
    assert adapter().validate_static(destination, "GPIO4 blink").success


def test_non_s3_esp_idf_target_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "CMakeLists.txt").write_text("include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n", encoding="utf-8")
    (tmp_path / "sdkconfig").write_text('CONFIG_IDF_TARGET="esp32"\n', encoding="utf-8")
    detection = adapter().detect_project(tmp_path)
    assert not detection.matched
    assert "unsupported ESP-IDF target" in detection.conflicts[0]


def test_missing_toolchain_and_hardware_are_unavailable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(esp_module.shutil, "which", lambda _: None)
    monkeypatch.delenv("IDF_PATH", raising=False)
    monkeypatch.setattr(esp_module, "list_ports", lambda: [])
    inst = adapter()
    assert inst.build(tmp_path).status == "UNAVAILABLE"
    assert inst.flash(tmp_path, device="COM7").status == "UNAVAILABLE"
    assert inst.serial_sample(device="COM7").status == "UNAVAILABLE"
    assert inst.hardware_run(tmp_path, serial_device="COM7").status == "UNAVAILABLE"


def test_hardware_validation_requires_marker_and_real_evidence() -> None:
    inst = adapter()
    assert inst.validate_hardware(serial_lines=None, expect=None, task="gpio", has_probe=False).status == "UNAVAILABLE"
    assert inst.validate_hardware(serial_lines=["boot ok"], expect=None, task="gpio", has_probe=True).status == "FAIL"
    assert inst.validate_hardware(serial_lines=["CEA:ESP32:PASS"], expect=None, task="gpio", has_probe=True).status == "PASS"


def test_gpio_and_uart_generators_are_bounded(tmp_path: Path) -> None:
    destination = tmp_path / "esp"
    assert adapter().create_template(destination, name="generated").success
    gpio = adapter().generate_peripheral(destination, "gpio", {"pin": 4})
    uart = adapter().generate_peripheral(destination, "uart", {"port": 0, "baud": 115200})
    unsupported = adapter().generate_peripheral(destination, "wifi", {})
    assert gpio.success and uart.success
    assert unsupported.status == "FAIL"
    cmake = (destination / "main" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "cea_gpio.c" in cmake and "cea_uart.c" in cmake

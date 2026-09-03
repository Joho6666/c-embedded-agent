from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.platforms.registry import PlatformRegistry, default_registry


@pytest.fixture
def registry() -> PlatformRegistry:
    return default_registry(Path(__file__).resolve().parents[2])


def test_platform_listing_matches_api_contract(registry: PlatformRegistry) -> None:
    items = registry.list_platforms()
    assert [item["id"] for item in items] == ["esp32s3-idf", "stm32f103-hal"]
    for item in items:
        assert {
            "id",
            "adapterId",
            "name",
            "platform",
            "status",
            "mcus",
            "boards",
            "frameworks",
            "toolchains",
            "capabilities",
            "reason",
        } <= item.keys()
    assert next(item for item in items if item["id"] == "stm32f103-hal")["status"] == "ready"
    assert next(item for item in items if item["id"] == "esp32s3-idf")["status"] == "experimental"


@pytest.mark.parametrize("selection", [
    {"mcu": "STM32F407VG"},
    {"platform": "RP2040"},
    {"adapter_id": "unknown"},
])
def test_unknown_and_f4_explicit_selection_is_unsupported(registry: PlatformRegistry, selection: dict[str, str]) -> None:
    result = registry.resolve_explicit(**selection)
    assert result.status == "unsupported"
    assert result.adapter is None


def test_conflicting_explicit_selection_is_ambiguous(registry: PlatformRegistry) -> None:
    result = registry.resolve_explicit(platform="STM32", mcu="ESP32-S3")
    assert result.status == "ambiguous"
    assert result.adapter is None


def test_detects_stm32f103_without_falling_back_for_f4(registry: PlatformRegistry, tmp_path: Path) -> None:
    f103 = tmp_path / "f103"
    f103.mkdir()
    (f103 / "board.ioc").write_text("Mcu.Name=STM32F103C8Tx\nMcu.Family=STM32F1\n", encoding="utf-8")
    assert registry.detect(f103).adapter.adapter_id == "stm32f103-hal"  # type: ignore[union-attr]

    f4 = tmp_path / "f4"
    f4.mkdir()
    (f4 / "board.ioc").write_text("Mcu.Name=STM32F407VGTx\nMcu.Family=STM32F4\n", encoding="utf-8")
    detected = registry.detect(f4)
    assert detected.status == "unsupported"
    assert detected.adapter is None
    assert "STM32F4" in (detected.reason or "")


def test_detects_esp32s3_and_rejects_mixed_platform_project(registry: PlatformRegistry, tmp_path: Path) -> None:
    esp = tmp_path / "esp"
    (esp / "main").mkdir(parents=True)
    (esp / "CMakeLists.txt").write_text("include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n", encoding="utf-8")
    (esp / "main" / "CMakeLists.txt").write_text('idf_component_register(SRCS "main.c")\n', encoding="utf-8")
    (esp / "sdkconfig.defaults").write_text('CONFIG_IDF_TARGET="esp32s3"\n', encoding="utf-8")
    result = registry.detect(esp)
    assert result.status == "resolved"
    assert result.adapter and result.adapter.adapter_id == "esp32s3-idf"

    (esp / "board.ioc").write_text("Mcu.Name=STM32F103C8Tx\n", encoding="utf-8")
    mixed = registry.detect(esp)
    assert mixed.status == "unsupported"
    assert mixed.adapter is None


def test_empty_directory_is_not_assumed_to_be_stm32(registry: PlatformRegistry, tmp_path: Path) -> None:
    result = registry.detect(tmp_path)
    assert result.status == "unsupported"
    assert result.adapter is None


def test_explicit_selection_must_not_conflict_with_detected_project(registry: PlatformRegistry, tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text(
        json.dumps({"adapterId": "stm32f103-hal", "mcu": "STM32F103C8T6"}), encoding="utf-8"
    )
    result = registry.resolve_project(tmp_path, adapter_id="esp32s3-idf")
    assert result.status == "ambiguous"
    assert "conflicts" in (result.reason or "")

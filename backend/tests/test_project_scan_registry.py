import json
from pathlib import Path

from app.tools import project_scan


def _write_f103(root: Path) -> None:
    (root / "Drivers" / "STM32F1xx_HAL_Driver").mkdir(parents=True)
    (root / "Core" / "Src").mkdir(parents=True)
    (root / "Core" / "Src" / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    (root / "board.ioc").write_text("Mcu.Name=STM32F103C8Tx\nMcu.Family=STM32F1\n", encoding="utf-8")


def _write_esp32s3(root: Path) -> None:
    (root / "main").mkdir(parents=True)
    (root / "CMakeLists.txt").write_text(
        'cmake_minimum_required(VERSION 3.16)\ninclude($ENV{IDF_PATH}/tools/cmake/project.cmake)\nproject(app)\n',
        encoding="utf-8",
    )
    (root / "main" / "CMakeLists.txt").write_text(
        'idf_component_register(SRCS "main.c" INCLUDE_DIRS ".")\n', encoding="utf-8"
    )
    (root / "main" / "main.c").write_text("void app_main(void) {}\n", encoding="utf-8")
    (root / "sdkconfig.defaults").write_text('CONFIG_IDF_TARGET="esp32s3"\n', encoding="utf-8")


def test_scan_uses_stm32_adapter_without_legacy_default(tmp_path: Path) -> None:
    _write_f103(tmp_path)

    result = project_scan.scan_existing_project(tmp_path)

    assert result["ok"] is True
    assert result["status"] == "resolved"
    assert result["adapterId"] == "stm32f103-hal"
    assert result["mcu"] == "STM32F103C8Tx"
    assert "build" in result["capabilities"]


def test_scan_rejects_unknown_project(tmp_path: Path) -> None:
    (tmp_path / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")

    result = project_scan.scan_existing_project(tmp_path)

    assert result["ok"] is False
    assert result["status"] == "unsupported"
    assert result["adapterId"] is None
    assert "no registered platform" in result["reason"]
    assert result["mcu"] is None


def test_scan_rejects_stm32f4_project(tmp_path: Path) -> None:
    (tmp_path / "Drivers" / "STM32F4xx_HAL_Driver").mkdir(parents=True)
    (tmp_path / "board.ioc").write_text("Mcu.Name=STM32F407VGTx\nMcu.Family=STM32F4\n", encoding="utf-8")

    result = project_scan.scan_existing_project(tmp_path)

    assert result["ok"] is False
    assert result["status"] == "unsupported"
    assert "STM32F4" in result["reason"]


def test_scan_rejects_conflicting_platform_signatures(tmp_path: Path) -> None:
    _write_f103(tmp_path)
    _write_esp32s3(tmp_path)

    result = project_scan.scan_existing_project(tmp_path)

    assert result["ok"] is False
    assert result["status"] == "ambiguous"
    assert "conflicting platform signatures" in result["reason"]


def test_import_writes_metadata_from_detected_adapter(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_esp32s3(source)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(project_scan, "_ws_root", lambda: workspace)
    monkeypatch.setattr(project_scan, "init_repo_safe", lambda _root: None)

    result = project_scan.import_existing_project(source, "Imported ESP")

    assert result["ok"] is True
    assert result["scan"]["adapterId"] == "esp32s3-idf"
    assert result["meta"]["platform"] == "ESP32"
    assert result["meta"]["mcu"] == "ESP32-S3"
    assert result["meta"]["framework"] == "ESP-IDF"
    assert result["meta"]["adapterId"] == "esp32s3-idf"
    assert result["meta"]["board"] == "ESP32-S3-DevKitC-1"
    saved = json.loads((workspace / result["projectId"] / "project.json").read_text(encoding="utf-8"))
    assert saved["adapterId"] == "esp32s3-idf"


def test_import_does_not_copy_unsupported_project(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(project_scan, "_ws_root", lambda: workspace)

    result = project_scan.import_existing_project(source)

    assert result["ok"] is False
    assert result["status"] == "unsupported"
    assert list(workspace.iterdir()) == []

from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app
from app.platforms.base import PlatformResult


client = TestClient(app)
main_module = importlib.import_module("app.main")


def test_platform_catalog_exposes_real_adapter_status_and_capabilities() -> None:
    response = client.get("/api/platforms")

    assert response.status_code == 200
    platforms = {item["adapterId"]: item for item in response.json()}
    assert platforms["stm32f103-hal"]["status"] == "ready"
    assert {"create", "build", "flash", "validate"} <= set(platforms["stm32f103-hal"]["capabilities"])
    assert platforms["esp32s3-idf"]["status"] in {"ready", "experimental"}
    assert platforms["esp32s3-idf"]["frameworks"] == ["ESP-IDF"]
    assert "8051-sdcc" in platforms
    assert platforms["8051-sdcc"]["status"] == "experimental"


def test_project_create_honors_explicit_esp32_selection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "workspace_root", tmp_path)

    response = client.post(
        "/api/projects",
        json={
            "name": "ESP32 GPIO",
            "platform": "ESP32",
            "mcu": "ESP32-S3",
            "framework": "ESP-IDF",
            "board": "esp32s3_devkitc_1",
            "adapterId": "esp32s3-idf",
        },
    )

    assert response.status_code == 200
    metadata = response.json()
    assert metadata["adapterId"] == "esp32s3-idf"
    assert metadata["platform"] == "ESP32"
    assert metadata["mcu"] == "ESP32-S3"
    assert metadata["framework"] == "ESP-IDF"
    assert {"create", "build", "flash", "validate"} <= set(metadata["capabilities"])
    assert (tmp_path / metadata["id"] / "CMakeLists.txt").is_file()


def test_project_create_rejects_unsupported_or_conflicting_selection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "workspace_root", tmp_path)

    unsupported = client.post(
        "/api/projects",
        json={"name": "F4", "platform": "STM32", "mcu": "STM32F407VGT6", "framework": "HAL"},
    )
    conflict = client.post(
        "/api/projects",
        json={
            "name": "Conflict",
            "platform": "ESP32",
            "mcu": "STM32F103C8T6",
            "framework": "ESP-IDF",
            "adapterId": "esp32s3-idf",
        },
    )

    assert unsupported.status_code == 422
    assert "unsupported" in unsupported.json()["detail"].lower()
    assert conflict.status_code == 422
    assert "conflicting" in conflict.json()["detail"].lower()
    assert list(tmp_path.iterdir()) == []


class _RecordingAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path, str]] = []

    def build(self, root: Path) -> PlatformResult:
        self.calls.append(("build", root, ""))
        return PlatformResult(
            "PASS",
            "build",
            "test-adapter",
            {
                "exit_code": 0,
                "stdout": "compiled",
                "stderr": "",
                "combined": "compiled",
                "artifacts": [{"name": "firmware.elf", "size": 123}],
                "memory": {"flash": 1024, "ram": 64},
            },
            evidence=["firmware.elf"],
        )

    def flash(self, root: Path) -> PlatformResult:
        self.calls.append(("flash", root, ""))
        return PlatformResult(
            "PASS", "flash", "test-adapter", {"exit_code": 0, "output": "verified"}, evidence=["probe"]
        )

    def validate_static(self, root: Path, task: str = "") -> PlatformResult:
        self.calls.append(("validate", root, task))
        return PlatformResult(
            "PASS",
            "validate",
            "test-adapter",
            {"passed": True, "score": 100, "checks": {"gpio": True}, "missing": []},
            evidence=["gpio"],
        )


def test_build_flash_and_validation_delegate_with_compatible_results(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    adapter = _RecordingAdapter()
    monkeypatch.setattr(main_module, "project_root", lambda project_id: project)
    monkeypatch.setattr(main_module, "_project_adapter", lambda root: adapter)
    monkeypatch.setattr(main_module, "record_from_output", lambda output, success: None)

    built = client.post("/api/projects/p1/build")
    flashed = client.post("/api/projects/p1/flash")
    validated = client.get("/api/validation", params={"projectId": "p1", "prompt": "GPIO output"})

    assert built.status_code == 200
    assert built.json() == {
        "success": True,
        "status": "PASS",
        "operation": "build",
        "adapterId": "test-adapter",
        "reason": None,
        "evidence": ["firmware.elf"],
        "exit_code": 0,
        "stdout": "compiled",
        "stderr": "",
        "combined": "compiled",
        "artifacts": [{"name": "firmware.elf", "size": 123}],
        "memory": {"flash": 1024, "ram": 64},
    }
    assert flashed.status_code == 200
    assert flashed.json()["success"] is True
    assert flashed.json()["status"] == "PASS"
    assert flashed.json()["output"] == "verified"
    assert validated.status_code == 200
    assert validated.json()["passed"] is True
    assert validated.json()["score"] == 100
    assert validated.json()["checks"] == {"gpio": True}
    assert adapter.calls == [
        ("build", project, ""),
        ("flash", project, ""),
        ("validate", project, "GPIO output"),
    ]

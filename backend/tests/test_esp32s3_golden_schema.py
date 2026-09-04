from __future__ import annotations

import json
from pathlib import Path

from app.config.settings import settings
from app.platforms.esp32s3.adapter import Esp32S3IdfAdapter


def test_esp32s3_golden_projects_schema() -> None:
    repo_root = settings.repo_root
    golden_root = repo_root / "examples" / "golden_esp32"
    assert golden_root.is_dir(), "examples/golden_esp32 directory must exist"

    expected_projects = [
        "esp32s3_gpio_blink",
        "esp32s3_uart",
        "esp32s3_pwm_ledc",
        "esp32s3_i2c",
        "esp32s3_spi",
        "esp32s3_adc",
        "esp32s3_freertos_task",
    ]

    adapter = Esp32S3IdfAdapter(repo_root)

    for name in expected_projects:
        project_dir = golden_root / name
        assert project_dir.is_dir(), f"Project {name} missing"

        # 1. project.json
        pj_file = project_dir / "project.json"
        assert pj_file.is_file(), f"{name}/project.json missing"
        pj = json.loads(pj_file.read_text(encoding="utf-8"))
        assert pj.get("adapterId") == "esp32s3-idf"
        assert pj.get("mcu") == "ESP32-S3"
        assert pj.get("platform") == "ESP32"
        assert pj.get("framework") == "ESP-IDF"
        assert pj.get("marker") == "CEA:ESP32:PASS"

        # 2. CMakeLists.txt
        cm_file = project_dir / "CMakeLists.txt"
        assert cm_file.is_file(), f"{name}/CMakeLists.txt missing"
        cm_text = cm_file.read_text(encoding="utf-8")
        assert "IDF_PATH" in cm_text
        assert "project.cmake" in cm_text

        # 3. sdkconfig.defaults
        sdk_file = project_dir / "sdkconfig.defaults"
        assert sdk_file.is_file(), f"{name}/sdkconfig.defaults missing"
        assert 'CONFIG_IDF_TARGET="esp32s3"' in sdk_file.read_text(encoding="utf-8")

        # 4. main/CMakeLists.txt & main/main.c
        main_c = project_dir / "main" / "main.c"
        assert main_c.is_file(), f"{name}/main/main.c missing"
        main_c_text = main_c.read_text(encoding="utf-8")
        assert "CEA:ESP32:PASS" in main_c_text
        assert "app_main" in main_c_text

        # 5. Adapter project detection
        evidence = adapter.detect_project(project_dir)
        assert evidence.matched is True
        assert evidence.confidence >= 0.8

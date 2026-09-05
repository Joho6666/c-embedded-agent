#!/usr/bin/env python3
"""Build and verify all 7 committed ESP32-S3 Golden projects."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = ROOT / "examples" / "golden_esp32"
EXPECTED = 7
EXPECTED_NAMES = [
    "esp32s3_adc",
    "esp32s3_freertos_task",
    "esp32s3_gpio_blink",
    "esp32s3_i2c",
    "esp32s3_pwm_ledc",
    "esp32s3_spi",
    "esp32s3_uart",
]


def check_schema() -> list[str]:
    errors: list[str] = []
    if not GOLDEN_ROOT.is_dir():
        return [f"Missing golden root: {GOLDEN_ROOT}"]

    projects = sorted(p for p in GOLDEN_ROOT.iterdir() if p.is_dir())
    if len(projects) != EXPECTED:
        errors.append(f"Expected {EXPECTED} ESP32-S3 golden projects, found {len(projects)}")

    for name in EXPECTED_NAMES:
        proj_dir = GOLDEN_ROOT / name
        if not proj_dir.is_dir():
            errors.append(f"Missing golden project: {name}")
            continue
        for req in ("CMakeLists.txt", "main/CMakeLists.txt", "main/main.c", "project.json", "sdkconfig.defaults"):
            if not (proj_dir / req).is_file():
                errors.append(f"Project {name} is missing required file: {req}")
        proj_json = proj_dir / "project.json"
        if proj_json.is_file():
            try:
                data = json.loads(proj_json.read_text(encoding="utf-8"))
                if data.get("adapterId") != "esp32s3-idf":
                    errors.append(f"{name}/project.json adapterId must be 'esp32s3-idf'")
                if data.get("mcu") != "ESP32-S3":
                    errors.append(f"{name}/project.json mcu must be 'ESP32-S3'")
            except json.JSONDecodeError as exc:
                errors.append(f"{name}/project.json invalid JSON: {exc}")
    return errors


def build_project(project: Path, use_docker: bool) -> tuple[bool, str]:
    if use_docker:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{ROOT}:/project",
            "espressif/idf:v6.1",
            "bash", "-lc",
            f"cd /project/examples/golden_esp32/{project.name} && idf.py set-target esp32s3 && idf.py build",
        ]
        res = subprocess.run(cmd, text=True, capture_output=True, check=False)
        return res.returncode == 0, res.stdout + res.stderr
    else:
        idf_py = shutil.which("idf.py")
        if not idf_py:
            return False, "idf.py not found in PATH"
        set_target = subprocess.run([idf_py, "set-target", "esp32s3"], cwd=project, text=True, capture_output=True, check=False)
        if set_target.returncode != 0:
            return False, set_target.stdout + set_target.stderr
        build = subprocess.run([idf_py, "build"], cwd=project, text=True, capture_output=True, check=False)
        return build.returncode == 0, build.stdout + build.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and build ESP32-S3 Golden projects")
    parser.add_argument("--schema-only", action="store_true", help="Only validate project files and schemas")
    parser.add_argument("--project", type=str, default=None, help="Build a single specific project")
    parser.add_argument("--docker", action="store_true", help="Force using docker image espressif/idf:v6.1")
    args = parser.parse_args()

    schema_errors = check_schema()
    if schema_errors:
        print("FAIL: ESP32-S3 Golden Schema Errors:")
        for err in schema_errors:
            print(f"  - {err}")
        return 1

    print(f"PASS: {EXPECTED}/{EXPECTED} ESP32-S3 Golden projects verified for schema and structure.")
    if args.schema_only:
        return 0

    has_idf = shutil.which("idf.py") is not None
    has_docker = shutil.which("docker") is not None
    use_docker = args.docker or (not has_idf and has_docker)

    if not has_idf and not use_docker:
        print("NOTICE: Neither native idf.py nor docker is available for compilation.")
        print("        Schema validation passed; compile gate requires ESP-IDF 6.1 or Docker.")
        return 0

    projects_to_build = [GOLDEN_ROOT / args.project] if args.project else [GOLDEN_ROOT / name for name in EXPECTED_NAMES]
    failed = []
    for proj in projects_to_build:
        print(f"Building {proj.name} ({'Docker' if use_docker else 'Native idf.py'})...", end=" ", flush=True)
        ok, logs = build_project(proj, use_docker)
        if ok:
            print("PASS")
        else:
            print("FAIL")
            failed.append(proj.name)
            print(logs[-2000:])

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

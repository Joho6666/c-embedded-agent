#!/usr/bin/env python3
"""Documentation drift gate.

Cross-checks version strings and support-matrix claims across
VERSION / CHANGELOG.md / README.md / RELEASE_REPORT.md / docs, and
verifies README claims against what actually exists on disk.

Exit 0 = consistent, 1 = drift found. Run in CI (Layer 1).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PLATFORM_KEYS = {
    "STM32F103 HAL": "templates/stm32f103_hal_official",
    "STM32F407": None,
    "ESP32": None,
    "8051": None,
}


def fail(issues: list[str], msg: str) -> None:
    issues.append(msg)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def main() -> int:
    issues: list[str] = []

    # 1. Version consistency
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    readme = read(ROOT / "README.md")
    changelog = read(ROOT / "CHANGELOG.md")
    release_report = read(ROOT / "RELEASE_REPORT.md")

    m = re.search(r"Version:\s*\*\*(.+?)\*\*", readme)
    readme_version = m.group(1).strip() if m else None
    if readme_version != version_file:
        fail(issues, f"VERSION={version_file!r} but README says {readme_version!r}")

    m = re.search(r"^##\s+(?!Unreleased)([0-9][^\s—-]*)", changelog, re.MULTILINE)
    changelog_version = m.group(1).rstrip("-").strip() if m else None
    if changelog_version and not version_file.startswith(changelog_version):
        fail(issues, f"CHANGELOG latest version {changelog_version!r} != VERSION {version_file!r}")

    m = re.search(r"^# RELEASE_REPORT.*?([0-9]+\.[0-9]+\.[0-9]+[^\s]*)", release_report, re.MULTILINE)
    report_version = m.group(1) if m else None
    if report_version and not version_file.startswith(report_version.split("-")[0]):
        fail(issues, f"RELEASE_REPORT version {report_version!r} does not match VERSION {version_file!r}")

    # 2. Support matrix: only STM32F103 may claim ✅ Build, and the template must exist
    matrix_rows = re.findall(r"^\|\s*([^|\n]+?)\s*\|([^|\n]+)\|", readme, re.MULTILINE)
    for name, cols in matrix_rows:
        name = name.strip()
        if name in PLATFORM_KEYS:
            build_ok = cols.split("|")[0].strip() == "✅"
            template = PLATFORM_KEYS[name]
            if build_ok and template and not (ROOT / template).is_dir():
                fail(issues, f"README matrix claims {name} build ✅ but {template} is missing")
            if build_ok and template is None:
                fail(issues, f"README matrix claims ✅ Build for unsupported platform {name}")

    if "STM32F103 HAL | ✅" not in readme.replace(" | ", " | ") and "| STM32F103 HAL | ✅" not in readme:
        fail(issues, "README support matrix lost its STM32F103 HAL row")

    # 3. Golden projects listed in README must exist on disk
    for path in re.findall(r"`(examples/golden/[a-z0-9_]+/)`", readme):
        if not (ROOT / path).is_dir():
            fail(issues, f"README lists golden project {path} which does not exist")

    # 4. Documented hardware status vocabulary must stay honest
    if "never PASS" not in readme and "never PASS" not in release_report:
        fail(issues, "NO FAKE PASS wording ('never PASS') missing from README/RELEASE_REPORT")

    if issues:
        print("DOCS DRIFT DETECTED:")
        for i in issues:
            print(f"  - {i}")
        return 1
    print(f"docs drift check OK (VERSION={version_file})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

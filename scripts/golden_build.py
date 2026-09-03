#!/usr/bin/env python3
"""Build every committed STM32 Golden and verify non-empty firmware artifacts."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = ROOT / "examples" / "golden"
EXPECTED = 11


def main() -> int:
    gcc = shutil.which("arm-none-eabi-gcc")
    make = shutil.which("make")
    if not gcc or not make:
        print("FAIL: arm-none-eabi-gcc and make are required for the Golden gate")
        return 2
    version = subprocess.check_output([gcc, "--version"], text=True).splitlines()[0]
    if "13.3.1" not in version:
        print(f"FAIL: expected ARM GCC 13.3.1, got {version}")
        return 2
    projects = sorted(path for path in GOLDEN_ROOT.iterdir() if path.is_dir() and path.name != "overlays" and (path / "Makefile").is_file())
    if len(projects) != EXPECTED:
        print(f"FAIL: expected {EXPECTED} Golden projects, found {len(projects)}")
        return 1
    failed: list[str] = []
    env = dict(os.environ)
    for project in projects:
        result = subprocess.run([make, "clean", "all", "-j2"], cwd=project, env=env, text=True, capture_output=True)
        artifacts = [project / f"firmware.{ext}" for ext in ("elf", "hex", "bin")]
        good = result.returncode == 0 and all(path.is_file() and path.stat().st_size > 0 for path in artifacts)
        print(f"{'PASS' if good else 'FAIL'} {project.name}")
        if not good:
            failed.append(project.name)
            print((result.stdout + result.stderr)[-3000:])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

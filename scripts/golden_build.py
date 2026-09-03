#!/usr/bin/env python3
"""Build every committed STM32 Golden and verify non-empty firmware artifacts."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = ROOT / "examples" / "golden"
EXPECTED = 11
FLASH_LIMIT = 64 * 1024
RAM_LIMIT = 20 * 1024


def _memory_ok(size_exe: str, project: Path) -> bool:
    result = subprocess.run([size_exe, "firmware.elf"], cwd=project, text=True, capture_output=True, check=False)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if result.returncode or len(lines) < 2:
        return False
    text, data, bss = (int(value) for value in lines[-1].split()[:3])
    return 0 < text + data <= FLASH_LIMIT and 0 <= data + bss <= RAM_LIMIT


def main() -> int:
    gcc = shutil.which("arm-none-eabi-gcc")
    make = shutil.which("make")
    size_exe = shutil.which("arm-none-eabi-size")
    if not gcc or not make or not size_exe:
        print("FAIL: arm-none-eabi-gcc, arm-none-eabi-size and make are required for the Golden gate")
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
    vendor = ROOT / "templates" / "stm32f103_hal_official" / "Drivers"
    with tempfile.TemporaryDirectory(prefix="cea-golden-") as temp_dir:
        temp_root = Path(temp_dir)
        for source in projects:
            project = temp_root / source.name
            shutil.copytree(source, project)
            shutil.copytree(vendor, project / "Drivers", dirs_exist_ok=True)
            clean = subprocess.run([make, "clean"], cwd=project, env=env, text=True, capture_output=True)
            result = subprocess.run([make, "all", "-j2"], cwd=project, env=env, text=True, capture_output=True)
            artifacts = [project / f"firmware.{ext}" for ext in ("elf", "hex", "bin")]
            good = clean.returncode == 0 and result.returncode == 0 and all(
                path.is_file() and path.stat().st_size > 0 for path in artifacts
            ) and _memory_ok(size_exe, project)
            print(f"{'PASS' if good else 'FAIL'} {source.name}")
            if not good:
                failed.append(source.name)
                print((clean.stdout + clean.stderr + result.stdout + result.stderr)[-3000:])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

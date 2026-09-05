#!/usr/bin/env python3
"""Build every committed 8051 Golden project with SDCC and verify real firmware artifacts."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = ROOT / "examples" / "golden_8051"
EXPECTED_MIN = 3
FLASH_LIMIT = 8 * 1024  # 8KB ROM for STC89C52RC
RAM_LIMIT = 512         # 512B RAM for STC89C52RC (256 internal + 256 aux)


def _check_hex_content(hex_path: Path) -> tuple[bool, int]:
    """Verify Intel HEX contains valid records and calculate total payload bytes."""
    if not hex_path.is_file() or hex_path.stat().st_size == 0:
        return False, 0
    text = hex_path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False, 0
    payload_bytes = 0
    has_eof = False
    has_data = False
    for line in lines:
        if not line.startswith(":"):
            continue
        if len(line) < 11:
            continue
        try:
            length = int(line[1:3], 16)
            record_type = line[7:9]
            if record_type == "00":
                has_data = True
                payload_bytes += length
            elif record_type == "01":
                has_eof = True
        except ValueError:
            return False, 0
    return (has_eof and has_data), payload_bytes


def main() -> int:
    sdcc = shutil.which("sdcc")
    make = shutil.which("make")
    packihx = shutil.which("packihx")

    if not sdcc or not make:
        print("FAIL: sdcc and make are required for 8051 Golden gate")
        return 2

    try:
        version_out = subprocess.check_output([sdcc, "--version"], text=True).splitlines()[0]
        print(f"SDCC compiler detected: {version_out}")
    except Exception:
        print("FAIL: unable to execute sdcc --version")
        return 2

    projects = sorted(
        path for path in GOLDEN_ROOT.iterdir()
        if path.is_dir() and (path / "Makefile").is_file() and (path / "main.c").is_file()
    )

    if len(projects) < EXPECTED_MIN:
        print(f"FAIL: expected at least {EXPECTED_MIN} 8051 Golden projects, found {len(projects)}")
        return 1

    failed: list[str] = []
    env = dict(os.environ)

    with tempfile.TemporaryDirectory(prefix="cea-8051-golden-") as temp_dir:
        temp_root = Path(temp_dir)
        for source in projects:
            project = temp_root / source.name
            shutil.copytree(source, project)

            clean = subprocess.run([make, "clean"], cwd=project, env=env, text=True, capture_output=True)
            result = subprocess.run([make, "all", "CC=sdcc", "PACKIHX=packihx"], cwd=project, env=env, text=True, capture_output=True)

            build_dir = project / "build"
            ihx_path = build_dir / "firmware.ihx"
            hex_path = build_dir / "firmware.hex"

            clean_ok = clean.returncode == 0
            build_ok = result.returncode == 0
            ihx_ok = ihx_path.is_file() and ihx_path.stat().st_size > 0
            hex_ok, payload_bytes = _check_hex_content(hex_path)
            rom_ok = 0 < payload_bytes <= FLASH_LIMIT

            good = clean_ok and build_ok and ihx_ok and hex_ok and rom_ok
            ihx_size = ihx_path.stat().st_size if ihx_path.is_file() else 0
            hex_size = hex_path.stat().st_size if hex_path.is_file() else 0
            status_str = "PASS" if good else "FAIL"
            print(f"{status_str} {source.name} (payload: {payload_bytes} B, ihx: {ihx_size} B, hex: {hex_size} B)")

            if not good:
                failed.append(source.name)
                print(f"--- Build failure diagnostics for {source.name} ---")
                print(f"Flags: clean_ok={clean_ok}, build_ok={build_ok}, ihx_ok={ihx_ok}, hex_ok={hex_ok}, rom_ok={rom_ok} (payload={payload_bytes})")
                print((clean.stdout + clean.stderr + result.stdout + result.stderr)[-3000:])

    if failed:
        print(f"8051 Golden Gate FAIL: {len(failed)} project(s) failed: {', '.join(failed)}")
        return 1

    print(f"8051 Golden Gate PASS: all {len(projects)} projects verified with SDCC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

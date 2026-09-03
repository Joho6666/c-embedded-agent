#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "templates" / "stm32f103_hal_official"
DST = Path(__file__).resolve().parent / "stm32f103_led"


def main() -> None:
    if not (SRC / "Drivers" / "CMSIS" / "Include" / "core_cm3.h").is_file():
        raise SystemExit("official template missing Drivers; run python scripts/sync_cubef1.py first")
    if DST.exists():
        for child in DST.iterdir():
            if child.name == "README.md":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    shutil.copytree(
        SRC,
        DST,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.elf", "*.hex", "*.bin", "*.o", "*.map", ".git", "README.md"),
    )


if __name__ == "__main__":
    main()

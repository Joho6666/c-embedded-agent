#!/usr/bin/env python3
"""Portable local pre-finish gate."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str], cwd: Path = ROOT) -> bool:
    print(f"\n== {label} ==")
    return subprocess.run(command, cwd=cwd).returncode == 0


def main() -> int:
    checks = [
        run("secret scan", [sys.executable, "scripts/secret_scan.py"]),
        run("quality invariants", [sys.executable, "scripts/quality_gate.py"]),
        run("backend", [sys.executable, "-m", "pytest", "-q"], ROOT / "backend"),
    ]
    print("\n" + ("PASS" if all(checks) else "FAIL") + ": pre-finish gate")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

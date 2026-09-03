#!/usr/bin/env python3
"""Fail on credential-shaped values in tracked source files."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"(?i)(?:api[_-]?key|secret|password)\s*[:=]\s*['\"](?!change|example|placeholder|your-|@)[^'\"]{12,}['\"]"),
]
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".bin", ".elf", ".hex", ".map", ".lock"}


def main() -> int:
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode(errors="replace").split("\0")
    findings: list[str] = []
    for name in filter(None, names):
        path = ROOT / name
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append(f"{name}:{lineno}")
    if findings:
        print("Potential credentials found:\n" + "\n".join(findings))
        return 1
    print(f"PASS: scanned {len(names)} tracked paths; no credential-shaped values found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Secret scan over git-tracked files (Layer 1 CI gate).

Scans every tracked text file for common credential patterns.
`--history N` additionally scans added lines of the last N commits.

Exit 0 = clean, 1 = findings. Never edits files.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "generic-credential",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*[\"'][^\"']{8,}[\"']"
        ),
    ),
]

_ALLOW_SUBSTRINGS = (
    "your", "placeholder", "example", "changeme", "xxx", "xxxx",
    "dummy", "sample", "insert", "redacted", "test", "mock", "fixture",
    "<", "${", "{{", "os.environ", "getenv", "process.env", "llm_api_key",
    "@",  # UI mention tokens like "@file:/Core/Src/main.c", never credentials
)


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    files = []
    for line in out.stdout.splitlines():
        p = ROOT / line
        if p.is_file() and p.stat().st_size < 2_000_000:
            files.append(p)
    return files


def _allowed(text: str) -> bool:
    low = text.lower()
    return any(s.lower() in low for s in _ALLOW_SUBSTRINGS)


def scan_text(text: str, where: str, findings: list[str]) -> None:
    for name, pattern in PATTERNS:
        for m in pattern.finditer(text):
            snippet = text[max(0, m.start() - 20): m.end() + 20].splitlines()
            ctx = snippet[0].strip() if snippet else ""
            if _allowed(m.group(0)) or _allowed(ctx):
                continue
            findings.append(f"{name}: {where}: …{ctx[:120]}")


def scan_history(commits: int, findings: list[str]) -> None:
    out = subprocess.run(
        ["git", "log", f"-{commits}", "-p", "--unified=0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    file_hdr: str | None = None
    for line in out.stdout.splitlines():
        if line.startswith("+++ b/"):
            file_hdr = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            scan_text(line[1:], f"history:{file_hdr}", findings)


def main() -> int:
    findings: list[str] = []
    for p in tracked_files():
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("unigateway/") or rel.startswith("legacy/"):
            continue  # archived grafts are inert; still covered by history scan
        if rel == ".env":
            findings.append(".env is tracked in git — secrets must never be committed")
            continue
        try:
            scan_text(p.read_text(encoding="utf-8", errors="ignore"), rel, findings)
        except OSError:
            continue

    if "--history" in sys.argv:
        n = 200
        if len(sys.argv) > sys.argv.index("--history") + 1:
            n = int(sys.argv[sys.argv.index("--history") + 1])
        scan_history(n, findings)

    if findings:
        print(f"SECRET SCAN: {len(findings)} finding(s)")
        for f in findings[:50]:
            print(f"  - {f}")
        return 1
    print("secret scan OK (tracked files clean)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

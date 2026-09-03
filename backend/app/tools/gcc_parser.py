from __future__ import annotations

import re
from typing import Any

GCC_LINE = re.compile(
    r"^(?P<file>[^:\n]+):(?P<line>\d+)(?::(?P<col>\d+))?:\s*"
    r"(?P<sev>fatal error|error|warning|note):\s*(?P<msg>.+)$"
)
UNDEF = re.compile(r"undefined reference to [`'\"](?P<sym>[^`'\"]+)[`'\"]")
MULTIDEF = re.compile(r"multiple definition of [`'\"](?P<sym>[^`'\"]+)[`'\"]")
LD_FILE = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+):")


def parse_gcc_output(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        m = GCC_LINE.match(line)
        if m:
            sev = m.group("sev")
            if sev == "fatal error":
                severity = "error"
            elif sev == "note":
                severity = "info"
            else:
                severity = sev
            out.append(
                {
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "column": int(m.group("col") or 1),
                    "severity": severity,
                    "message": m.group("msg").strip(),
                    "source": "gcc",
                }
            )
            continue
        um = UNDEF.search(line)
        if um:
            fm = LD_FILE.match(line)
            out.append(
                {
                    "file": fm.group("file") if fm else "",
                    "line": int(fm.group("line")) if fm else 0,
                    "column": 1,
                    "severity": "error",
                    "message": f"undefined reference to `{um.group('sym')}`",
                    "source": "ld",
                }
            )
            continue
        mm = MULTIDEF.search(line)
        if mm:
            fm = LD_FILE.match(line)
            out.append(
                {
                    "file": fm.group("file") if fm else "",
                    "line": int(fm.group("line")) if fm else 0,
                    "column": 1,
                    "severity": "error",
                    "message": f"multiple definition of `{mm.group('sym')}`",
                    "source": "ld",
                }
            )
    return out

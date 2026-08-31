from __future__ import annotations

import re
from typing import Any

GCC_LINE = re.compile(
    r"^(?P<file>[^:\n]+):(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?P<sev>error|warning|note):\s*(?P<msg>.+)$"
)


def parse_gcc_output(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in text.splitlines():
        m = GCC_LINE.match(raw.strip())
        if not m:
            continue
        out.append(
            {
                "file": m.group("file"),
                "line": int(m.group("line")),
                "column": int(m.group("col") or 1),
                "severity": m.group("sev") if m.group("sev") != "note" else "info",
                "message": m.group("msg").strip(),
            }
        )
    return out

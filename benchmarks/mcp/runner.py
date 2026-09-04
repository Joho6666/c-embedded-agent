"""MCP vs plain-harness benchmark runner.

Does not invent scores. Without ARM GCC or an LLM harness, writes SKIPPED.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    tasks = json.loads((Path(__file__).parent / "tasks.json").read_text(encoding="utf-8"))
    from app.core import build_project, inspect_project
    from app.tools.detect import gcc_installed

    gcc = gcc_installed()
    results = []
    for task in tasks:
        root = REPO / task["project"]
        inspect = inspect_project(root)
        compile_status = "SKIPPED"
        skip_reason = None
        status = "SKIPPED"
        if not root.is_dir():
            compile_status = "UNAVAILABLE"
            skip_reason = f"missing project {task['project']}"
            status = "UNAVAILABLE"
        elif task.get("must_compile"):
            if not gcc:
                compile_status = "UNAVAILABLE"
                skip_reason = "ARM GCC not installed — not faking compile"
                status = "SKIPPED"
            else:
                built = build_project(root)
                compile_status = built.get("status") or "FAIL"
                status = "PASS" if built.get("status") == "SUCCESS" else "FAIL"
        else:
            status = "PASS" if inspect.get("status") == "SUCCESS" else "FAIL"
            compile_status = "SKIPPED"
        results.append(
            {
                "id": task["id"],
                "mode": "cea_mcp",
                "status": status,
                "skip_reason": skip_reason,
                "compile": compile_status,
                "hardware": "SKIPPED",
                "artifacts": [],
                "notes": "plain_harness comparison SKIPPED — no LLM harness configured; not faking Agent vs Baseline",
                "inspected": inspect.get("status"),
            }
        )
    summary = {
        "generated_at": _now(),
        "gcc": gcc,
        "llm": False,
        "plain_harness": "SKIPPED",
        "cea_mcp": results,
        "reason": "LLM / Harness not configured — not faking comparison numbers",
    }
    out = Path(__file__).parent / "latest-summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

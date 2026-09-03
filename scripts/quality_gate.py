#!/usr/bin/env python3
"""Fast repository invariants that do not need network access or hardware."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TASK_FIELDS = {"id", "prompt", "platform", "category", "fixture", "oracle", "requirements", "environment", "evidence"}


def main() -> int:
    failures: list[str] = []
    required_docs = ["AGENTS.md", "CURRENT_ARCHITECTURE.md", "PROJECT_STATE.md", "ARCHITECTURE.md", "docs/INDEX.md"]
    for name in required_docs:
        if not (ROOT / name).is_file():
            failures.append(f"missing {name}")

    tasks = []
    for path in sorted((ROOT / "benchmarks" / "stm32f103").glob("*.json")):
        if path.name in {"latest-summary.json", "results.json"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = REQUIRED_TASK_FIELDS - data.keys()
        if missing:
            failures.append(f"{path.relative_to(ROOT)} missing {sorted(missing)}")
        tasks.append(data)
    ids = [str(task.get("id")) for task in tasks]
    if len(tasks) < 50:
        failures.append(f"benchmark contains {len(tasks)} tasks; expected >=50")
    if len(ids) != len(set(ids)):
        failures.append("benchmark task ids are not unique")

    for relative in ["benchmarks/stm32f103/latest-summary.json", "benchmarks/comparison-summary.json"]:
        data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        if data.get("tasks") == 0 and not (data.get("skipped") or data.get("status") in {"SKIPPED", "NOT RUN"}):
            failures.append(f"{relative} reports zero tasks without a skip status")

    if failures:
        print("FAIL:\n- " + "\n- ".join(failures))
        return 1
    print(f"PASS: documentation and {len(tasks)} benchmark task definitions validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

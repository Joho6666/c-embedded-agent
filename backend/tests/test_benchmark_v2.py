"""Phase H tests: Outcome Memory, Error Memory v2 counters, benchmark v2 tasks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.db import connect
from app.tools.error_memory import ensure_schema as em_ensure, get_error, mark_fix_result
from app.tools.outcome_memory import list_outcomes, record_outcome, summary

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from benchmarks.benchmark import apply_inject  # noqa: E402


# ---------------------------------------------------------------- outcome memory

def test_outcome_memory_record_and_summary():
    rid = record_outcome(
        run_id="run-test-om-1",
        task_id="01",
        task_type="benchmark",
        domain="PERIPHERAL_CONFIG",
        model="test-model",
        attempts=2,
        repair_count=1,
        input_tokens=100,
        output_tokens=50,
        elapsed_s=1.5,
        build_success=True,
        hardware_success=False,
        detail={"semantic_ok": True},
    )
    assert rid > 0
    items = list_outcomes(domain="PERIPHERAL_CONFIG")
    match = [i for i in items if i["run_id"] == "run-test-om-1"]
    assert match and match[0]["build_success"] is True and match[0]["hardware_success"] is False
    s = summary()
    assert s["totalRuns"] >= 1
    assert s["byDomain"]["PERIPHERAL_CONFIG"]["buildSuccess"] > 0


def test_outcome_memory_hardware_only_with_evidence_flag():
    record_outcome(
        run_id="run-test-om-hw",
        task_type="hardware_run",
        domain="Blue Pill",
        build_success=True,
        hardware_success=True,
        detail={"status": "PASS"},
    )
    items = list_outcomes(domain="Blue Pill")
    assert any(i["run_id"] == "run-test-om-hw" and i["hardware_success"] for i in items)


# ---------------------------------------------------------------- error memory v2

def test_error_memory_v2_columns_and_counters():
    em_ensure()
    eid = "hal-uart-init-undef"
    before = get_error(eid)
    mark_fix_result(eid, success=True, hardware_pass=True)
    after = get_error(eid)
    assert after["verifiedCount"] == (before["verifiedCount"] or 0) + 1
    assert after["hardwareVerifiedCount"] == (before["hardwareVerifiedCount"] or 0) + 1
    mark_fix_result(eid, success=False)
    assert get_error(eid)["failedCount"] == (before["failedCount"] or 0) + 1


def test_error_memory_schema_has_v2_columns():
    em_ensure()
    with connect() as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(error_memories)").fetchall()}
    assert {"platform", "toolchain", "phase", "error_class", "verified_count", "hardware_verified_count"} <= cols


# ---------------------------------------------------------------- benchmark v2

def test_benchmark_task_set_is_50_with_domains():
    task_dir = ROOT / "benchmarks" / "stm32f103"
    files = [
        p
        for p in sorted(task_dir.glob("*.json"))
        if p.name not in {"results.json", "latest-summary.json"}
    ]
    assert len(files) == 50
    domains = set()
    for p in files:
        t = json.loads(p.read_text(encoding="utf-8"))
        assert t.get("must_compile") is True
        assert t.get("prompt")
        assert t.get("domain")
        assert t.get("level") in {"regression", "capability"}
        assert isinstance(t.get("inject") or [], list)
        domains.add(t["domain"])
    assert domains <= {
        "PERIPHERAL_CONFIG",
        "COMPILE_REPAIR",
        "SAFETY",
        "DEBUGGING",
        "LONG_HORIZON",
        "CONTEXT",
    }


def test_apply_inject_replaces_once(tmp_path: Path):
    f = tmp_path / "Core" / "Src" / "main.c"
    f.parent.mkdir(parents=True)
    f.write_text("MX_GPIO_Init();\nHAL_Delay(500);\n", encoding="utf-8")
    applied = apply_inject(
        tmp_path,
        [{"file": "Core/Src/main.c", "find": "HAL_Delay(500)", "replace": "HAL_Delay(500000)", "count": 1}],
    )
    assert applied
    assert "HAL_Delay(500000)" in f.read_text(encoding="utf-8")


def test_apply_inject_missing_file_is_noop(tmp_path: Path):
    applied = apply_inject(
        tmp_path,
        [{"file": "Nope/main.c", "find": "x", "replace": "y"}],
    )
    assert applied == []

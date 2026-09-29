"""Outcome Memory — the long-term record of what the agent actually achieved.

One row per executed task/run: which agent+model, how many attempts, tokens,
time, and — critically — the three success levels (build / simulation /
hardware). This becomes the evidence-based data asset the Router later uses
to pick models per task type. Nothing is written without a real run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.db import connect, now

SCHEMA_READY = False


def ensure_schema() -> None:
    global SCHEMA_READY
    if SCHEMA_READY:
        return
    with connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS outcome_memories (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_id TEXT,
              task_id TEXT,
              task_type TEXT,
              domain TEXT,
              agent TEXT,
              model TEXT,
              attempts INTEGER DEFAULT 1,
              repair_count INTEGER DEFAULT 0,
              input_tokens INTEGER DEFAULT 0,
              output_tokens INTEGER DEFAULT 0,
              elapsed_s REAL DEFAULT 0,
              build_success INTEGER DEFAULT 0,
              simulation_success INTEGER DEFAULT 0,
              hardware_success INTEGER DEFAULT 0,
              detail TEXT,
              recorded_at TEXT
            )"""
        )
    SCHEMA_READY = True


def record_outcome(
    *,
    run_id: str | None = None,
    task_id: str | None = None,
    task_type: str | None = None,
    domain: str | None = None,
    agent: str = "cea-agent",
    model: str | None = None,
    attempts: int = 1,
    repair_count: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    elapsed_s: float = 0.0,
    build_success: bool = False,
    simulation_success: bool = False,
    hardware_success: bool = False,
    detail: Any = None,
) -> int:
    """Record one real outcome. hardware_success=True requires evidence."""
    ensure_schema()
    with connect() as con:
        cur = con.execute(
            """INSERT INTO outcome_memories
               (run_id, task_id, task_type, domain, agent, model, attempts, repair_count,
                input_tokens, output_tokens, elapsed_s, build_success, simulation_success,
                hardware_success, detail, recorded_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                task_id,
                task_type,
                domain,
                agent,
                model,
                max(1, int(attempts)),
                max(0, int(repair_count)),
                max(0, int(input_tokens)),
                max(0, int(output_tokens)),
                float(elapsed_s),
                1 if build_success else 0,
                1 if simulation_success else 0,
                1 if hardware_success else 0,
                json.dumps(detail, ensure_ascii=False)[:4000] if detail is not None else None,
                now(),
            ),
        )
        return int(cur.lastrowid or 0)


def list_outcomes(domain: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    ensure_schema()
    with connect() as con:
        if domain:
            rows = con.execute(
                "SELECT * FROM outcome_memories WHERE domain=? ORDER BY id DESC LIMIT ?",
                (domain, int(limit)),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM outcome_memories ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
    return [_row(r) for r in rows]


def _row(r: Any) -> dict[str, Any]:
    d = dict(r)
    d["build_success"] = bool(d.get("build_success"))
    d["simulation_success"] = bool(d.get("simulation_success"))
    d["hardware_success"] = bool(d.get("hardware_success"))
    if d.get("detail"):
        try:
            d["detail"] = json.loads(d["detail"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def summary() -> dict[str, Any]:
    """Aggregate pass rates per domain — the Router's future input."""
    ensure_schema()
    with connect() as con:
        rows = con.execute(
            """SELECT domain, COUNT(*) AS n,
                      AVG(build_success) AS build_rate,
                      AVG(simulation_success) AS sim_rate,
                      AVG(hardware_success) AS hw_rate,
                      AVG(elapsed_s) AS avg_elapsed,
                      AVG(input_tokens + output_tokens) AS avg_tokens
               FROM outcome_memories GROUP BY domain"""
        ).fetchall()
    by_domain = {}
    for r in rows:
        by_domain[r["domain"] or "unknown"] = {
            "runs": int(r["n"]),
            "buildSuccess": round(float(r["build_rate"] or 0), 4),
            "simulationSuccess": round(float(r["sim_rate"] or 0), 4),
            "hardwareSuccess": round(float(r["hw_rate"] or 0), 4),
            "avgElapsedS": round(float(r["avg_elapsed"] or 0), 2),
            "avgTokens": round(float(r["avg_tokens"] or 0), 1),
        }
    with connect() as con:
        total = con.execute("SELECT COUNT(*) AS n FROM outcome_memories").fetchone()
    return {"totalRuns": int(total["n"]), "byDomain": by_domain}

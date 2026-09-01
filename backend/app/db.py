from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  prompt TEXT,
  status TEXT,
  iteration INTEGER DEFAULT 0,
  model TEXT,
  started_at TEXT,
  finished_at TEXT
);
CREATE TABLE IF NOT EXISTS run_events (
  id TEXT PRIMARY KEY,
  run_id TEXT,
  type TEXT,
  payload TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS file_changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  path TEXT,
  before TEXT,
  after TEXT
);
CREATE TABLE IF NOT EXISTS builds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  project_id TEXT,
  success INTEGER,
  exit_code INTEGER,
  output TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT,
  name TEXT,
  size INTEGER,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS model_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  model TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER,
  tool_calls INTEGER
);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
  title, body, source, section, page, mcu, kind,
  tokenize = 'porter'
);
"""


def _db_path() -> Path:
    p = settings.workspace_root
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p / "agent.sqlite"


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_run(run_id: str, project_id: str, prompt: str, status: str, model: str = "") -> None:
    with connect() as con:
        con.execute(
            """INSERT INTO runs(id, project_id, prompt, status, model, started_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET status=excluded.status""",
            (run_id, project_id, prompt, status, model, now()),
        )


def finish_run(run_id: str, status: str, iteration: int = 0) -> None:
    with connect() as con:
        con.execute(
            "UPDATE runs SET status=?, iteration=?, finished_at=? WHERE id=?",
            (status, iteration, now(), run_id),
        )


def save_event(event: dict[str, Any]) -> None:
    with connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO run_events(id, run_id, type, payload, created_at) VALUES(?,?,?,?,?)",
            (
                event.get("id"),
                event.get("runId"),
                event.get("type"),
                json.dumps(event, ensure_ascii=False),
                event.get("timestamp") or now(),
            ),
        )


def save_file_change(run_id: str, path: str, before: str, after: str) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO file_changes(run_id, path, before, after) VALUES(?,?,?,?)",
            (run_id, path, before, after),
        )


def save_build(run_id: str, project_id: str, result: dict[str, Any]) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO builds(run_id, project_id, success, exit_code, output) VALUES(?,?,?,?,?)",
            (
                run_id,
                project_id,
                1 if result.get("success") else 0,
                result.get("exit_code", 1),
                str(result.get("combined", ""))[-8000:],
            ),
        )


def save_model_call(
    run_id: str,
    model: str,
    usage: dict[str, Any] | None,
    latency_ms: int,
    tool_calls: int,
) -> None:
    usage = usage or {}
    with connect() as con:
        con.execute(
            """INSERT INTO model_calls(run_id, model, input_tokens, output_tokens, latency_ms, tool_calls)
               VALUES(?,?,?,?,?,?)""",
            (
                run_id,
                model,
                int(usage.get("prompt_tokens") or 0),
                int(usage.get("completion_tokens") or 0),
                latency_ms,
                tool_calls,
            ),
        )


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute(
            "SELECT id, project_id, prompt, status, iteration, model, started_at, finished_at FROM runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def load_run(run_id: str) -> dict[str, Any] | None:
    with connect() as con:
        row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        events = con.execute(
            "SELECT payload FROM run_events WHERE run_id=? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        data = dict(row)
        data["events"] = [json.loads(e["payload"]) for e in events]
        return data

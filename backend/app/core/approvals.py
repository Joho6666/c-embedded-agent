"""Unified approval policy — levels and their default rules.

Wraps the existing gates (code-mode approval, MCP confirm flags, flash
budget, DANGEROUS_HARDWARE tokens) into one declarative policy surface so
the UI, MCP and CLI agree on what is auto / ask / deny.
"""

from __future__ import annotations

from typing import Any

from app.hardware.safety import DANGEROUS_OPERATIONS, LEVELS, OPERATION_LEVEL

RULES: dict[str, str] = {
    "SAFE_READ": "auto",
    "SAFE_BUILD": "auto",
    "PROJECT_WRITE": "ask_once",  # code mode enforces; auto mode proceeds per existing policy
    "HARDWARE_FLASH": "ask_once",  # MCP confirm=true; Web flash budget (max 8/process)
    "DEBUG_CONTROL": "auto",  # read-only halt/dump/register reads
    "GIT_WRITE": "auto",  # pre-run snapshot + undo
    "DANGEROUS_HARDWARE": "deny",  # explicit one-time token required (safety.py)
    "EXTERNAL_WRITE": "ask_every_time",
    "SYSTEM_CHANGE": "deny",
}

# operation → level (single source of truth; mirrors safety.OPERATION_LEVEL)
OPERATIONS: dict[str, str] = dict(OPERATION_LEVEL)


def policy() -> dict[str, Any]:
    return {
        "levels": {k: {"default": v, **({"rule": RULES[k]} if k in RULES else {})} for k, v in LEVELS.items()},
        "dangerousOperations": list(DANGEROUS_OPERATIONS),
        "operationLevels": OPERATIONS,
        "notes": [
            "DANGEROUS_HARDWARE operations are BLOCKED by default; a single-use approval token (safety.approve_operation) unlocks exactly one execution.",
            "Compile success never authorizes hardware actions.",
        ],
    }

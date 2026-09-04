from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.types import FAIL, MUTATING, SUCCESS, UNKNOWN, envelope
from app.tools.periph_gen import configure_peripheral as _configure


def configure_peripheral_at(root: Path, kind: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    kind_n = (kind or "").strip().lower()
    if not kind_n:
        return envelope(status=FAIL, side_effect=MUTATING, ok=False, reason="kind is required")
    result = _configure(root, kind_n, args or {})
    if not result.get("ok"):
        reason = str(result.get("reason") or "configure failed")
        status = UNKNOWN if reason.startswith("unknown peripheral") else FAIL
        return envelope(status=status, side_effect=MUTATING, **result)
    return envelope(status=SUCCESS, side_effect=MUTATING, **result)

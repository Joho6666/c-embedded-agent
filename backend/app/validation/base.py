from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from app.tools.filesystem import list_files, read_file


class ValidationResult(TypedDict, total=False):
    passed: bool
    score: float
    checks: dict[str, bool]
    missing: list[str]


def core_source_text(root: Path) -> str:
    blobs: list[str] = []
    try:
        rels = list_files(root)
    except OSError:
        return ""
    for rel in rels:
        if rel.endswith((".c", ".h")) and "Drivers/" not in rel and "Middlewares/" not in rel:
            try:
                blobs.append(read_file(root, rel))
            except OSError:
                continue
    return "\n".join(blobs)


def read_makefile(root: Path) -> str:
    try:
        return read_file(root, "Makefile")
    except FileNotFoundError:
        return ""


def read_hal_conf(root: Path) -> str:
    try:
        return read_file(root, "Core/Inc/stm32f1xx_hal_conf.h")
    except FileNotFoundError:
        return ""


def module_enabled(conf: str, macro: str) -> bool:
    import re

    return bool(re.search(rf"^\s*#define\s+{re.escape(macro)}\s*$", conf, re.M))


def result_from_checks(checks: dict[str, bool]) -> dict[str, Any]:
    n = max(len(checks), 1)
    missing = [k for k, v in checks.items() if not v]
    score = round(sum(1 for v in checks.values() if v) / n, 4)
    return {
        "passed": len(missing) == 0,
        "score": score,
        "checks": checks,
        "missing": missing,
    }


def result_dict(
    *,
    passed: bool,
    score: float,
    checks: dict[str, bool],
    missing: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "passed": passed,
        "score": score,
        "checks": checks,
        "missing": missing,
    }
    if extra:
        out.update(extra)
    return out

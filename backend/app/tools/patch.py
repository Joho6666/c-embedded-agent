from __future__ import annotations

import re
from pathlib import Path

from app.workspace.paths import assert_writable, resolve_in_root

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(ValueError):
    pass


def apply_patch(root: Path, rel: str, patch: str, *, advanced: bool = False) -> str:
    """Apply a unified diff. Returns new content or raises PatchError('PATCH_FAILED: ...')."""
    norm = assert_writable(rel, advanced=advanced)
    path = resolve_in_root(root, norm)
    if not path.is_file():
        raise PatchError(f"PATCH_FAILED: file not found: {norm}")
    original = path.read_text(encoding="utf-8", errors="replace")
    new = _apply_unified(original, patch)
    path.write_text(new, encoding="utf-8")
    return new


def _apply_unified(original: str, patch: str) -> str:
    src = original.splitlines()
    ended_nl = original.endswith("\n")
    hunks = _parse_hunks(patch)
    if not hunks:
        raise PatchError("PATCH_FAILED: no hunks")
    out: list[str] = []
    cursor = 0
    for old_start, old_count, specs in hunks:
        start = max(old_start - 1, 0)
        if start < cursor:
            raise PatchError("PATCH_FAILED: overlapping hunks")
        out.extend(src[cursor:start])
        old_idx = start
        produced: list[str] = []
        old_consumed = 0
        for tag, text in specs:
            if tag == " ":
                if old_idx >= len(src) or src[old_idx] != text:
                    raise PatchError(f"PATCH_FAILED: context mismatch at line {old_idx + 1}")
                produced.append(text)
                old_idx += 1
                old_consumed += 1
            elif tag == "-":
                if old_idx >= len(src) or src[old_idx] != text:
                    raise PatchError(f"PATCH_FAILED: delete mismatch at line {old_idx + 1}")
                old_idx += 1
                old_consumed += 1
            elif tag == "+":
                produced.append(text)
            else:
                raise PatchError(f"PATCH_FAILED: bad hunk line: {tag}")
        if old_count and old_consumed != old_count:
            raise PatchError("PATCH_FAILED: old count mismatch")
        out.extend(produced)
        cursor = old_idx
    out.extend(src[cursor:])
    body = "\n".join(out)
    if ended_nl or original == "":
        if not body.endswith("\n"):
            body += "\n"
    return body


def _parse_hunks(patch: str) -> list[tuple[int, int, list[tuple[str, str]]]]:
    hunks: list[tuple[int, int, list[tuple[str, str]]]] = []
    current: list[tuple[str, str]] | None = None
    old_start = 1
    old_count = 0
    for raw in patch.splitlines():
        if raw.startswith(("diff ", "index ", "---", "+++")):
            continue
        hm = HUNK_RE.match(raw)
        if hm:
            if current is not None:
                hunks.append((old_start, old_count, current))
            old_start = int(hm.group(1))
            old_count = int(hm.group(2) or "1")
            current = []
            continue
        if current is None:
            continue
        if not raw:
            current.append((" ", ""))
            continue
        tag = raw[0]
        if tag == "\\":
            continue
        if tag not in " +-":
            continue
        current.append((tag, raw[1:]))
    if current is not None:
        hunks.append((old_start, old_count, current))
    return hunks

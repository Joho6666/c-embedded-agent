from __future__ import annotations

import threading

_lock = threading.Lock()
_cursors: dict[str, int] = {}


def next_index(key: str, n: int) -> int:
    if n <= 0:
        return 0
    with _lock:
        i = _cursors.get(key, 0)
        _cursors[key] = (i + 1) % n
        return i % n

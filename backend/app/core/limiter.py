from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def _prune(q: deque[float], window: float, now: float) -> None:
    while q and now - q[0] > window:
        q.popleft()


def allow(key: str, limit: int, window_s: float = 60.0) -> bool:
    if limit <= 0:
        return True
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        _prune(q, window_s, now)
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def remaining(key: str, limit: int, window_s: float = 60.0) -> int:
    if limit <= 0:
        return 10**9
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        _prune(q, window_s, now)
        return max(0, limit - len(q))

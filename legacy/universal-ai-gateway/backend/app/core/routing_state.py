from __future__ import annotations

from app.core.state import get_state


def next_index(key: str, n: int) -> int:
    return get_state().next_round_robin(key, n)

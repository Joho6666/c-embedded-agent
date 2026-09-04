from __future__ import annotations

from app.core.state import get_state


def allow(key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool:
    return get_state().sliding_window_allow(key, limit, window_s, amount)


def peek(key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool:
    return get_state().sliding_window_peek(key, limit, window_s, amount)


def add(key: str, amount: int = 1, window_s: float = 60.0) -> None:
    get_state().sliding_window_add(key, amount, window_s)


def remaining(key: str, limit: int, window_s: float = 60.0) -> int:
    if limit <= 0:
        return 10**9
    used = get_state().sliding_window_used(key, window_s)
    return max(0, limit - used)


def used(key: str, window_s: float = 60.0) -> int:
    return get_state().sliding_window_used(key, window_s)

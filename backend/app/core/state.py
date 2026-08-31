from __future__ import annotations

import socket
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Any, Iterator, Protocol


class StateBackend(Protocol):
    def increment(self, key: str, amount: int = 1) -> int: ...
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, expire_s: int | None = None) -> None: ...
    def expire(self, key: str, seconds: int) -> None: ...
    def sliding_window_allow(self, key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool: ...
    def sliding_window_peek(self, key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool: ...
    def sliding_window_add(self, key: str, amount: int = 1, window_s: float = 60.0) -> None: ...
    def sliding_window_used(self, key: str, window_s: float = 60.0) -> int: ...
    def next_round_robin(self, key: str, n: int) -> int: ...
    def smooth_wrr_pick(self, key: str, items: list[tuple[str, int]]) -> str | None: ...
    def lock(self, key: str, ttl_s: float = 5.0) -> Iterator[None]: ...


class MemoryStateBackend:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._kv: dict[str, tuple[str, float | None]] = {}
        self._hits: dict[str, deque[tuple[float, int]]] = defaultdict(deque)
        self._cursors: dict[str, int] = {}
        self._wrr: dict[str, dict[str, int]] = defaultdict(dict)
        self._locks: dict[str, threading.Lock] = defaultdict(threading.Lock)

    def _prune_kv(self, now: float) -> None:
        dead = [k for k, (_, exp) in self._kv.items() if exp is not None and exp <= now]
        for k in dead:
            self._kv.pop(k, None)

    def increment(self, key: str, amount: int = 1) -> int:
        with self._lock:
            now = time.monotonic()
            self._prune_kv(now)
            cur, exp = self._kv.get(key, ("0", None))
            try:
                val = int(cur) + amount
            except ValueError:
                val = amount
            self._kv[key] = (str(val), exp)
            return val

    def get(self, key: str) -> str | None:
        with self._lock:
            now = time.monotonic()
            self._prune_kv(now)
            item = self._kv.get(key)
            return item[0] if item else None

    def set(self, key: str, value: str, expire_s: int | None = None) -> None:
        with self._lock:
            exp = time.monotonic() + expire_s if expire_s else None
            self._kv[key] = (value, exp)

    def expire(self, key: str, seconds: int) -> None:
        with self._lock:
            item = self._kv.get(key)
            if item:
                self._kv[key] = (item[0], time.monotonic() + seconds)

    def _prune_hits(self, key: str, window_s: float, now: float) -> deque[tuple[float, int]]:
        q = self._hits[key]
        while q and now - q[0][0] > window_s:
            q.popleft()
        return q

    def sliding_window_used(self, key: str, window_s: float = 60.0) -> int:
        now = time.monotonic()
        with self._lock:
            q = self._prune_hits(key, window_s, now)
            return sum(amount for _, amount in q)

    def sliding_window_peek(self, key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool:
        if limit <= 0:
            return True
        return self.sliding_window_used(key, window_s) + amount <= limit

    def sliding_window_add(self, key: str, amount: int = 1, window_s: float = 60.0) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._prune_hits(key, window_s, now)
            q.append((now, max(0, amount)))

    def sliding_window_allow(self, key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            q = self._prune_hits(key, window_s, now)
            used = sum(a for _, a in q)
            if used + amount > limit:
                return False
            q.append((now, max(0, amount)))
            return True

    def next_round_robin(self, key: str, n: int) -> int:
        if n <= 0:
            return 0
        with self._lock:
            i = self._cursors.get(key, 0)
            self._cursors[key] = (i + 1) % n
            return i % n

    def smooth_wrr_pick(self, key: str, items: list[tuple[str, int]]) -> str | None:
        if not items:
            return None
        with self._lock:
            current = self._wrr[key]
            live = {cid for cid, _ in items}
            for stale in [cid for cid in current if cid not in live]:
                current.pop(stale, None)
            total = sum(max(1, w) for _, w in items)
            best_id = items[0][0]
            best_cur = -10**18
            for cid, weight in items:
                w = max(1, weight)
                current[cid] = current.get(cid, 0) + w
                if current[cid] > best_cur:
                    best_cur = current[cid]
                    best_id = cid
            current[best_id] = current.get(best_id, 0) - total
            return best_id

    @contextmanager
    def lock(self, key: str, ttl_s: float = 5.0) -> Iterator[None]:
        lk = self._locks[key]
        lk.acquire()
        try:
            yield
        finally:
            lk.release()


_LUA_ALLOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local amount = tonumber(ARGV[4])
local member = ARGV[5]
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local members = redis.call('ZRANGE', key, 0, -1)
local used = 0
for _, m in ipairs(members) do
  local a = tonumber(string.match(m, ':([0-9]+)$')) or 1
  used = used + a
end
if limit > 0 and (used + amount) > limit then
  return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, math.ceil(window) + 5)
return 1
"""

_LUA_USED = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local members = redis.call('ZRANGE', key, 0, -1)
local used = 0
for _, m in ipairs(members) do
  local a = tonumber(string.match(m, ':([0-9]+)$')) or 1
  used = used + a
end
return used
"""

_LUA_WRR = """
local key = KEYS[1]
local n = tonumber(ARGV[1])
local best_id = ARGV[2]
local best = -1e18
local total = 0
local ids = {}
local weights = {}
for i = 0, n - 1 do
  local id = ARGV[2 + i * 2]
  local w = tonumber(ARGV[3 + i * 2]) or 1
  if w < 1 then w = 1 end
  ids[i + 1] = id
  weights[i + 1] = w
  total = total + w
end
for i = 1, n do
  local id = ids[i]
  local cur = tonumber(redis.call('HGET', key, id) or '0') + weights[i]
  redis.call('HSET', key, id, cur)
  if cur > best then
    best = cur
    best_id = id
  end
end
local picked = tonumber(redis.call('HGET', key, best_id) or '0') - total
redis.call('HSET', key, best_id, picked)
redis.call('EXPIRE', key, 86400)
return best_id
"""


class RedisStateBackend:
    def __init__(self, client: Any) -> None:
        self._r = client
        self._seq = 0
        self._lock = threading.Lock()

    def increment(self, key: str, amount: int = 1) -> int:
        return int(self._r.incrby(key, amount))

    def get(self, key: str) -> str | None:
        val = self._r.get(key)
        if val is None:
            return None
        if isinstance(val, bytes):
            return val.decode("utf-8")
        return str(val)

    def set(self, key: str, value: str, expire_s: int | None = None) -> None:
        if expire_s:
            self._r.set(key, value, ex=expire_s)
        else:
            self._r.set(key, value)

    def expire(self, key: str, seconds: int) -> None:
        self._r.expire(key, seconds)

    def sliding_window_used(self, key: str, window_s: float = 60.0) -> int:
        now = time.time()
        return int(self._r.eval(_LUA_USED, 1, key, now, window_s) or 0)

    def sliding_window_peek(self, key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool:
        if limit <= 0:
            return True
        return self.sliding_window_used(key, window_s) + amount <= limit

    def sliding_window_add(self, key: str, amount: int = 1, window_s: float = 60.0) -> None:
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex}:{max(0, amount)}"
        pipe = self._r.pipeline()
        pipe.zadd(key, {member: now})
        pipe.zremrangebyscore(key, "-inf", now - window_s)
        pipe.expire(key, int(window_s) + 5)
        pipe.execute()

    def sliding_window_allow(self, key: str, limit: int, window_s: float = 60.0, amount: int = 1) -> bool:
        if limit <= 0:
            return True
        now = time.time()
        with self._lock:
            self._seq += 1
            member = f"{now}:{self._seq}:{max(0, amount)}"
        return int(self._r.eval(_LUA_ALLOW, 1, key, now, window_s, limit, max(0, amount), member) or 0) == 1

    def next_round_robin(self, key: str, n: int) -> int:
        if n <= 0:
            return 0
        val = int(self._r.incr(f"rr:{key}"))
        return (val - 1) % n

    def smooth_wrr_pick(self, key: str, items: list[tuple[str, int]]) -> str | None:
        if not items:
            return None
        args: list[Any] = [len(items)]
        for cid, weight in items:
            args.extend([cid, max(1, int(weight))])
        picked = self._r.eval(_LUA_WRR, 1, f"wrr:{key}", *args)
        if isinstance(picked, bytes):
            return picked.decode("utf-8")
        return str(picked) if picked is not None else items[0][0]

    @contextmanager
    def lock(self, key: str, ttl_s: float = 5.0) -> Iterator[None]:
        token = uuid.uuid4().hex
        ok = self._r.set(f"lock:{key}", token, nx=True, ex=max(1, int(ttl_s)))
        deadline = time.time() + ttl_s
        while not ok and time.time() < deadline:
            time.sleep(0.01)
            ok = self._r.set(f"lock:{key}", token, nx=True, ex=max(1, int(ttl_s)))
        if not ok:
            raise TimeoutError(f"lock timeout: {key}")
        try:
            yield
        finally:
            cur = self._r.get(f"lock:{key}")
            if cur == token or (isinstance(cur, bytes) and cur.decode("utf-8") == token):
                self._r.delete(f"lock:{key}")


_backend: StateBackend | None = None
_status: dict[str, str] = {"mode": "memory", "redis": "disabled", "error": ""}


def discover_redis_url(explicit: str) -> str:
    if explicit.strip():
        return explicit.strip()
    try:
        sock = socket.create_connection(("redis", 6379), timeout=0.25)
        sock.close()
        return "redis://redis:6379/0"
    except OSError:
        return ""


def _connect_redis(url: str) -> Any:
    import redis

    client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1.5, socket_timeout=2.0)
    client.ping()
    return client


def init_state(redis_url: str | None = None, force_memory: bool = False) -> StateBackend:
    global _backend, _status
    if force_memory:
        _backend = MemoryStateBackend()
        _status = {"mode": "memory", "redis": "disabled", "error": ""}
        return _backend
    url = discover_redis_url(redis_url or "")
    if not url:
        _backend = MemoryStateBackend()
        _status = {"mode": "memory", "redis": "disabled", "error": ""}
        return _backend
    try:
        client = _connect_redis(url)
        _backend = RedisStateBackend(client)
        _status = {"mode": "redis", "redis": "connected", "error": ""}
        return _backend
    except Exception as exc:  # noqa: BLE001
        _backend = MemoryStateBackend()
        _status = {"mode": "memory", "redis": "error", "error": str(exc)[:240]}
        return _backend


def get_state() -> StateBackend:
    global _backend
    if _backend is None:
        from app.core.config import get_settings

        init_state(get_settings().redis_url)
    assert _backend is not None
    return _backend


def state_status() -> dict[str, str]:
    if _backend is None:
        get_state()
    return dict(_status)


def reset_state(backend: StateBackend | None = None) -> StateBackend:
    global _backend, _status
    _backend = backend or MemoryStateBackend()
    if isinstance(_backend, RedisStateBackend):
        _status = {"mode": "redis", "redis": "connected", "error": ""}
    else:
        _status = {"mode": "memory", "redis": "disabled", "error": ""}
    return _backend

"""Local smoke test. Do not run in CI with real API keys.

Env:
  SMOKE_BASE_URL  default http://127.0.0.1:8000
  SMOKE_API_KEY
  SMOKE_MODEL
"""

from __future__ import annotations

import json
import os
import sys
import time

import httpx


def main() -> int:
    base = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    key = os.environ.get("SMOKE_API_KEY", "")
    model = os.environ.get("SMOKE_MODEL", "mock-small")
    if not key:
        print("SMOKE_API_KEY is required", file=sys.stderr)
        return 2
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    results: list[dict] = []

    def record(name: str, status: int, **extra):
        row = {"name": name, "status": status, **extra}
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))

    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{base}/v1/models", headers=headers)
        record("models", r.status_code, body=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:200])

        started = time.perf_counter()
        r = client.post(
            f"{base}/v1/chat/completions",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": "ping"}]},
        )
        latency = int((time.perf_counter() - started) * 1000)
        payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        record(
            "chat",
            r.status_code,
            latency=latency,
            model=(payload.get("model") if isinstance(payload, dict) else None),
            usage=(payload.get("usage") if isinstance(payload, dict) else None),
            error=payload.get("error") if isinstance(payload, dict) else None,
        )

        started = time.perf_counter()
        ttft = None
        with client.stream(
            "POST",
            f"{base}/v1/chat/completions",
            headers=headers,
            json={"model": model, "stream": True, "messages": [{"role": "user", "content": "ping"}]},
        ) as stream:
            status = stream.status_code
            for chunk in stream.iter_bytes():
                if chunk and ttft is None:
                    ttft = int((time.perf_counter() - started) * 1000)
            latency = int((time.perf_counter() - started) * 1000)
        record("stream", status, ttft=ttft, latency=latency)

        started = time.perf_counter()
        r = client.post(f"{base}/v1/responses", headers=headers, json={"model": model, "input": "ping"})
        latency = int((time.perf_counter() - started) * 1000)
        payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        record("responses", r.status_code, latency=latency, error=payload.get("error") if isinstance(payload, dict) else None)

    failed = [r for r in results if r["status"] >= 400]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

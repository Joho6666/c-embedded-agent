from __future__ import annotations

from typing import Any


def normalize_usage(payload: dict[str, Any] | None) -> dict[str, int]:
    usage = (payload or {}).get("usage") or {}
    prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    cached = int(usage.get("cached_tokens") or usage.get("prompt_tokens_details", {}).get("cached_tokens") or 0)
    if isinstance(usage.get("prompt_tokens_details"), dict):
        cached = int(usage["prompt_tokens_details"].get("cached_tokens") or cached)
    reasoning = 0
    details = usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
    if isinstance(details, dict):
        reasoning = int(details.get("reasoning_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    return {
        "input_tokens": prompt,
        "output_tokens": completion,
        "cached_tokens": cached,
        "reasoning_tokens": reasoning,
        "total_tokens": total,
    }


def parse_sse_usage(obj: dict[str, Any]) -> dict[str, int] | None:
    if not isinstance(obj, dict):
        return None
    if obj.get("usage"):
        return normalize_usage(obj)
    return None

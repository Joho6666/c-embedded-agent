from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.providers.base import AdapterContext, BaseProviderAdapter, ChatResult, UpstreamError


class ExternalBridgeAdapter(BaseProviderAdapter):
    """Reserved for Codex / Antigravity / CLI OAuth bridges. Not used in MVP."""

    name = "external_bridge"

    async def list_models(self, ctx: AdapterContext) -> list[str]:
        raise UpstreamError(501, "ExternalBridgeAdapter is reserved; not enabled in MVP")

    async def health_check(self, ctx: AdapterContext) -> tuple[bool, str, int]:
        return False, "not enabled in MVP", 501

    async def chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        raise UpstreamError(501, "ExternalBridgeAdapter is reserved; not enabled in MVP")

    async def stream_chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> AsyncIterator[bytes]:
        raise UpstreamError(501, "ExternalBridgeAdapter is reserved; not enabled in MVP")
        yield b""  # pragma: no cover

    async def responses(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        raise UpstreamError(501, "ExternalBridgeAdapter is reserved; not enabled in MVP")

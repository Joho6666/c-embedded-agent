from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


class UpstreamError(Exception):
    def __init__(self, status_code: int, message: str, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.retryable = retryable


@dataclass
class AdapterContext:
    base_url: str
    api_key: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    timeout_s: float = 60.0


@dataclass
class ChatResult:
    status_code: int
    payload: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)


class BaseProviderAdapter(ABC):
    name: str = "base"
    supports_chat: bool = True
    supports_responses: bool = True
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_embeddings: bool = False
    supports_images: bool = False
    supports_audio: bool = False
    supports_reasoning: bool = False

    @abstractmethod
    async def list_models(self, ctx: AdapterContext) -> list[str]:
        ...

    @abstractmethod
    async def health_check(self, ctx: AdapterContext) -> tuple[bool, str, int]:
        ...

    @abstractmethod
    async def chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        ...

    @abstractmethod
    async def stream_chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> AsyncIterator[bytes]:
        ...

    @abstractmethod
    async def responses(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        ...

    def normalize_request(self, body: dict[str, Any]) -> dict[str, Any]:
        return dict(body)

    def normalize_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


def retryable_status(code: int) -> bool:
    return code in {429, 500, 502, 503, 504}

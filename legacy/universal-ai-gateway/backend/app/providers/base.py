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


@dataclass
class ProviderCapabilities:
    chat: bool = True
    responses: bool = True
    native_responses: bool = False
    streaming: bool = True
    tools: bool = True
    vision: bool = False
    embeddings: bool = False
    images: bool = False
    audio: bool = False
    reasoning: bool = False
    structured_output: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "chat": self.chat,
            "responses": self.responses,
            "nativeResponses": self.native_responses,
            "streaming": self.streaming,
            "tools": self.tools,
            "vision": self.vision,
            "embeddings": self.embeddings,
            "images": self.images,
            "audio": self.audio,
            "reasoning": self.reasoning,
            "structuredOutput": self.structured_output,
        }


class BaseProviderAdapter(ABC):
    name: str = "base"
    supports_chat: bool = True
    supports_responses: bool = True
    supports_native_responses: bool = False
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_embeddings: bool = False
    supports_images: bool = False
    supports_audio: bool = False
    supports_reasoning: bool = False
    supports_structured_output: bool = False

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=self.supports_chat,
            responses=self.supports_responses,
            native_responses=self.supports_native_responses,
            streaming=self.supports_streaming,
            tools=self.supports_tools,
            vision=self.supports_vision,
            embeddings=self.supports_embeddings,
            images=self.supports_images,
            audio=self.supports_audio,
            reasoning=self.supports_reasoning,
            structured_output=self.supports_structured_output,
        )

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

    async def responses(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        from app.providers.transform import chat_body_from_responses, responses_from_chat

        result = await self.chat_completion(ctx, chat_body_from_responses(body))
        return responses_from_chat(result)

    async def stream_responses(self, ctx: AdapterContext, body: dict[str, Any]) -> AsyncIterator[bytes]:
        from app.providers.transform import chat_body_from_responses

        async for chunk in self.stream_chat_completion(ctx, chat_body_from_responses(body)):
            yield chunk

    def normalize_request(self, body: dict[str, Any]) -> dict[str, Any]:
        return dict(body)

    def normalize_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


def retryable_status(code: int) -> bool:
    return code in {429, 500, 502, 503, 504}

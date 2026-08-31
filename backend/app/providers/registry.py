from app.providers.base import BaseProviderAdapter, ProviderCapabilities
from app.providers.external_bridge import ExternalBridgeAdapter
from app.providers.gemini import GeminiAdapter
from app.providers.ollama import OllamaAdapter
from app.providers.openai_compatible import OpenAICompatibleAdapter

_ADAPTERS: dict[str, BaseProviderAdapter] = {
    "openai_compatible": OpenAICompatibleAdapter(),
    "custom": OpenAICompatibleAdapter(),
    "gemini": GeminiAdapter(),
    "ollama": OllamaAdapter(),
    "external_bridge": ExternalBridgeAdapter(),
}


def get_adapter(provider_type: str) -> BaseProviderAdapter:
    return _ADAPTERS.get(provider_type, _ADAPTERS["openai_compatible"])


def adapter_capabilities() -> dict[str, dict[str, bool]]:
    out: dict[str, dict[str, bool]] = {}
    for name, adapter in _ADAPTERS.items():
        caps = adapter.capabilities() if hasattr(adapter, "capabilities") else ProviderCapabilities()
        data = caps.as_dict()
        data.update(
            {
                "supports_chat": adapter.supports_chat,
                "supports_responses": adapter.supports_responses,
                "supports_streaming": adapter.supports_streaming,
                "supports_tools": adapter.supports_tools,
                "supports_vision": adapter.supports_vision,
                "supports_embeddings": adapter.supports_embeddings,
                "supports_images": adapter.supports_images,
                "supports_audio": adapter.supports_audio,
                "supports_reasoning": adapter.supports_reasoning,
            }
        )
        out[name] = data
    return out

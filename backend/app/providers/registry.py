from app.providers.base import BaseProviderAdapter
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

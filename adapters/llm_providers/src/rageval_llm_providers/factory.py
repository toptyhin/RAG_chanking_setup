"""Build LLM providers from saved config."""

from __future__ import annotations

from rageval_llm_providers.catalog import ModelPurpose, RemoteModelInfo
from rageval_llm_providers.config import LlmConfig, TextLlmProvider
from rageval_llm_providers.gigachat import GigaChatProvider
from rageval_llm_providers.ollama import OllamaProvider
from rageval_llm_providers.openrouter import OpenRouterProvider
from rageval_llm_providers.protocol import ConnectionTestResult, LlmProvider


def build_provider(config: LlmConfig) -> LlmProvider:
    if config.provider == TextLlmProvider.ollama:
        return OllamaProvider(config.ollama)
    if config.provider == TextLlmProvider.openrouter:
        return OpenRouterProvider(config.openrouter)
    if config.provider == TextLlmProvider.gigachat:
        return GigaChatProvider(config.gigachat)
    raise ValueError(f"unsupported LLM provider: {config.provider!r}")


def test_connection(config: LlmConfig) -> ConnectionTestResult:
    return build_provider(config).ping()


def list_model_infos(
    config: LlmConfig,
    *,
    purpose: ModelPurpose = ModelPurpose.text,
) -> list[RemoteModelInfo]:
    provider = build_provider(config)
    list_infos = getattr(provider, "list_model_infos", None)
    if callable(list_infos):
        return list(list_infos(purpose=purpose))
    return [
        RemoteModelInfo(id=mid, name=mid)
        for mid in provider.list_models()
        if isinstance(mid, str) and mid.strip()
    ]

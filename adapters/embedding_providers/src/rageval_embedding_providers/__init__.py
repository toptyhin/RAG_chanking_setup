"""Embedding provider adapters (Ollama / ST / OpenRouter / GigaChat)."""

from rageval_embedding_providers.config import (
    EmbeddingConfig,
    EmbeddingConfigStore,
    EmbeddingProviderKind,
    GigaChatEmbeddingSettings,
    OllamaEmbeddingSettings,
    OpenRouterEmbeddingSettings,
    SentenceTransformersSettings,
    mask_secret,
)
from rageval_embedding_providers.factory import (
    build_embedding_provider,
    build_remote_client,
    is_remote_embedding_provider,
    list_model_infos,
    list_models,
    test_connection,
)
from rageval_embedding_providers.remote_provider import RemoteEmbeddingProvider
from rageval_llm_providers.protocol import ConnectionTestResult

__all__ = [
    "ConnectionTestResult",
    "EmbeddingConfig",
    "EmbeddingConfigStore",
    "EmbeddingProviderKind",
    "GigaChatEmbeddingSettings",
    "OllamaEmbeddingSettings",
    "OpenRouterEmbeddingSettings",
    "RemoteEmbeddingProvider",
    "SentenceTransformersSettings",
    "build_embedding_provider",
    "build_remote_client",
    "is_remote_embedding_provider",
    "list_model_infos",
    "list_models",
    "mask_secret",
    "test_connection",
]

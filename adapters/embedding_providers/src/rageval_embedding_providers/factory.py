"""Build embedding remote clients / connection tests from saved config."""

from __future__ import annotations

import os

from rageval_embedding_providers.config import EmbeddingConfig, EmbeddingProviderKind
from rageval_embedding_providers.gigachat import GigaChatEmbeddingClient
from rageval_embedding_providers.ollama import OllamaEmbeddingClient
from rageval_embedding_providers.openrouter import OpenRouterEmbeddingClient
from rageval_embedding_providers.protocol import EmbeddingRemoteProvider
from rageval_embedding_providers.remote_provider import (
    DEFAULT_BATCH_SIZE,
    RemoteEmbeddingProvider,
)
from rageval_llm_providers.catalog import (
    ModelPurpose,
    RemoteModelInfo,
    resolve_embedding_dimensions,
)
from rageval_llm_providers.protocol import ConnectionTestResult

_REMOTE_KINDS = frozenset(
    {
        EmbeddingProviderKind.ollama,
        EmbeddingProviderKind.openrouter,
        EmbeddingProviderKind.gigachat,
    }
)

DEFAULT_EMBED_TIMEOUT_SEC = 120.0


def _env_positive_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def remote_embed_timeout_sec() -> float:
    """Per-request timeout for remote embedding HTTP calls."""
    return _env_positive_float("RAGEVAL_EMBED_TIMEOUT_SEC", DEFAULT_EMBED_TIMEOUT_SEC)


def remote_embed_batch_size() -> int:
    """How many texts one remote embedding HTTP request may carry."""
    return _env_positive_int("RAGEVAL_EMBED_BATCH_SIZE", DEFAULT_BATCH_SIZE)


def is_remote_embedding_provider(kind: EmbeddingProviderKind | str) -> bool:
    return EmbeddingProviderKind(kind) in _REMOTE_KINDS


def build_remote_client(
    config: EmbeddingConfig,
    *,
    model_id: str | None = None,
) -> EmbeddingRemoteProvider | None:
    mid = (model_id or "").strip() or None
    timeout = remote_embed_timeout_sec()
    if config.provider == EmbeddingProviderKind.ollama:
        settings = config.ollama
        if mid:
            settings = settings.model_copy(update={"model": mid})
        return OllamaEmbeddingClient(settings, timeout=timeout)
    if config.provider == EmbeddingProviderKind.openrouter:
        settings = config.openrouter
        if mid:
            settings = settings.model_copy(update={"model": mid})
        return OpenRouterEmbeddingClient(settings, timeout=timeout)
    if config.provider == EmbeddingProviderKind.gigachat:
        settings = config.gigachat
        if mid:
            settings = settings.model_copy(update={"model": mid})
        return GigaChatEmbeddingClient(settings, timeout=timeout)
    return None


def build_embedding_provider(
    config: EmbeddingConfig,
    *,
    model_id: str | None = None,
) -> RemoteEmbeddingProvider | None:
    """Build an EmbeddingProvider for remote configs; ST returns None (registry path)."""
    if not is_remote_embedding_provider(config.provider):
        return None
    mid = (model_id or "").strip()
    if not mid:
        if config.provider == EmbeddingProviderKind.ollama:
            mid = config.ollama.model.strip()
        elif config.provider == EmbeddingProviderKind.openrouter:
            mid = config.openrouter.model.strip()
        else:
            mid = config.gigachat.model.strip()
    if not mid:
        raise ValueError("remote embedding model_id is required")
    client = build_remote_client(config, model_id=mid)
    if client is None:
        return None
    return RemoteEmbeddingProvider(
        client,
        model_name=mid,
        batch_size=remote_embed_batch_size(),
    )


def test_connection(config: EmbeddingConfig) -> ConnectionTestResult:
    if config.provider == EmbeddingProviderKind.sentence_transformers:
        model = config.sentence_transformers.model.strip()
        if not model:
            return ConnectionTestResult(
                ok=False,
                latency_ms=0.0,
                message="sentence_transformers model is empty",
                model=None,
            )
        return ConnectionTestResult(
            ok=True,
            latency_ms=0.0,
            message=f"local sentence_transformers · model {model}",
            model=model,
            models=[model],
        )
    client = build_remote_client(config)
    if client is None:
        return ConnectionTestResult(
            ok=False,
            latency_ms=0.0,
            message=f"unsupported embedding provider: {config.provider!r}",
            model=None,
        )
    return client.ping()


def list_models(config: EmbeddingConfig) -> list[str]:
    if config.provider == EmbeddingProviderKind.sentence_transformers:
        model = config.sentence_transformers.model.strip()
        return [model] if model else []
    client = build_remote_client(config)
    if client is None:
        return []
    return client.list_models()


def list_model_infos(
    config: EmbeddingConfig,
    *,
    purpose: ModelPurpose = ModelPurpose.embeddings,
) -> list[RemoteModelInfo]:
    if config.provider == EmbeddingProviderKind.sentence_transformers:
        model = config.sentence_transformers.model.strip()
        if not model:
            return []
        dim, dims = resolve_embedding_dimensions(model)
        return [
            RemoteModelInfo(
                id=model,
                name=model,
                dimension=dim,
                dimensions=dims,
            )
        ]
    client = build_remote_client(config)
    if client is None:
        return []
    list_infos = getattr(client, "list_model_infos", None)
    if callable(list_infos):
        return list(list_infos(purpose=purpose))
    return [
        RemoteModelInfo(id=mid, name=mid)
        for mid in client.list_models()
        if isinstance(mid, str) and mid.strip()
    ]

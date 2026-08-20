"""Build EmbeddingService from settings."""

from __future__ import annotations

from rageval_cache_fs import FsEmbeddingCache
from rageval_domain.settings import Settings
from rageval_embedding import (
    DEFAULT_MODEL,
    EmbeddingService,
    HashEmbeddingProvider,
    SentenceTransformerProvider,
)


def build_embedding_service(settings: Settings) -> EmbeddingService:
    cache = FsEmbeddingCache(settings.cache_dir)
    provider_name = settings.embedding_provider.lower().strip()
    if provider_name in {"hash", "hash-emb", "test"}:
        provider = HashEmbeddingProvider()
    elif provider_name in {"sentence_transformers", "st", "local"}:
        model = settings.embedding_model or DEFAULT_MODEL
        provider = SentenceTransformerProvider(model_name=model)
    else:
        raise ValueError(f"unknown EMBEDDING_PROVIDER: {settings.embedding_provider}")
    return EmbeddingService(provider, cache=cache)

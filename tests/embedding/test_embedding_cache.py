"""Embedding service + FS cache."""

from __future__ import annotations

from pathlib import Path

from rageval_cache_fs import FsEmbeddingCache
from rageval_domain import Chunk, ChunkSet
from rageval_embedding import EmbeddingService, HashEmbeddingProvider


def test_encode_two_texts_same_dim() -> None:
    provider = HashEmbeddingProvider(dimension=32)
    vectors = provider.encode(["hello", "world"])
    assert vectors.shape == (2, 32)
    norms = (vectors**2).sum(axis=1) ** 0.5
    assert abs(float(norms[0]) - 1.0) < 1e-5
    assert abs(float(norms[1]) - 1.0) < 1e-5


def test_cache_avoids_second_encode(tmp_path: Path) -> None:
    provider = HashEmbeddingProvider(dimension=16)
    cache = FsEmbeddingCache(tmp_path / "cache")
    service = EmbeddingService(provider, cache=cache)
    chunk_set = ChunkSet(
        id="chunks_demo",
        project_id="proj",
        chunks=[
            Chunk(chunk_id="c1", doc_id="d1", text="alpha"),
            Chunk(chunk_id="c2", doc_id="d1", text="beta"),
        ],
    )
    first = service.embed_chunk_set(chunk_set)
    assert first.cache_hit is False
    assert provider.encode_calls == 1

    second = service.embed_chunk_set(chunk_set)
    assert second.cache_hit is True
    assert provider.encode_calls == 1
    assert (first.vectors == second.vectors).all()

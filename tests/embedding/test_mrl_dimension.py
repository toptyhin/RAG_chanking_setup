"""MRL / dimension truncate tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from rageval_cache_fs import FsEmbeddingCache
from rageval_domain import Chunk, ChunkSet
from rageval_embedding import EmbeddingService, HashEmbeddingProvider, truncate_vectors


def test_truncate_vectors_renorms() -> None:
    vectors = np.array([[3.0, 4.0, 0.0, 0.0]], dtype=np.float32)
    out = truncate_vectors(vectors, 2)
    assert out.shape == (1, 2)
    assert abs(float(np.linalg.norm(out[0])) - 1.0) < 1e-5


def test_embedding_service_mrl_cache_key_includes_dim(tmp_path: Path) -> None:
    provider = HashEmbeddingProvider(dimension=32)
    cache = FsEmbeddingCache(tmp_path / "cache")
    chunk_set = ChunkSet(
        id="chunks_mrl",
        project_id="proj",
        chunks=[Chunk(chunk_id="c1", doc_id="d1", text="alpha")],
    )
    svc16 = EmbeddingService(provider, cache=cache, dimension=16)
    svc32 = EmbeddingService(provider, cache=cache, dimension=32)

    first16 = svc16.embed_chunk_set(chunk_set)
    assert first16.dimension == 16
    assert first16.vectors.shape == (1, 16)
    assert first16.cache_hit is False

    second16 = svc16.embed_chunk_set(chunk_set)
    assert second16.cache_hit is True

    first32 = svc32.embed_chunk_set(chunk_set)
    assert first32.dimension == 32
    assert first32.vectors.shape == (1, 32)
    # The 16-d request cached the native vector before truncating, so the
    # native-dimension request reuses it without another model encode.
    assert first32.cache_hit is True
    assert provider.encode_calls == 1

"""Embedding service with optional FS cache and MRL truncate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rageval_domain import ChunkSet
from rageval_embedding.protocol import EmbeddingProvider


@dataclass(slots=True)
class EmbeddedTexts:
    ids: list[str]
    vectors: np.ndarray
    model_name: str
    dimension: int
    cache_hit: bool = False


class EmbeddingCacheProtocol:
    def get(
        self, *, chunk_set_id: str, model_name: str, dimension: int
    ) -> tuple[list[str], np.ndarray] | None: ...

    def set(
        self,
        *,
        chunk_set_id: str,
        model_name: str,
        dimension: int,
        ids: list[str],
        vectors: np.ndarray,
    ) -> None: ...


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return (vectors / norms).astype(np.float32)


def truncate_vectors(vectors: np.ndarray, dimension: int) -> np.ndarray:
    """MRL-style truncate to first `dimension` components, then L2-renormalize."""
    if vectors.ndim != 2:
        raise ValueError("vectors must be 2-D")
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    if vectors.shape[1] == dimension:
        return vectors.astype(np.float32, copy=False)
    if dimension > vectors.shape[1]:
        raise ValueError(
            f"cannot truncate to dimension {dimension} from {vectors.shape[1]}"
        )
    return _l2_normalize(vectors[:, :dimension].astype(np.float32, copy=False))


class EmbeddingService:
    def __init__(
        self,
        provider: EmbeddingProvider,
        cache: EmbeddingCacheProtocol | None = None,
        *,
        dimension: int | None = None,
    ) -> None:
        """If ``dimension`` is set and smaller than provider dim, truncate (MRL)."""
        if dimension is not None and dimension <= 0:
            raise ValueError("dimension must be positive")
        if dimension is not None and dimension > provider.dimension:
            raise ValueError(
                f"target dimension {dimension} exceeds provider dimension {provider.dimension}"
            )
        self.provider = provider
        self.cache = cache
        self._target_dimension = dimension

    @property
    def dimension(self) -> int:
        return self._target_dimension if self._target_dimension is not None else self.provider.dimension

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = self.provider.encode(texts)
        if self._target_dimension is not None:
            vectors = truncate_vectors(vectors, self._target_dimension)
        return vectors

    def embed_chunk_set(self, chunk_set: ChunkSet) -> EmbeddedTexts:
        ids = [c.chunk_id for c in chunk_set.chunks]
        texts = [c.text for c in chunk_set.chunks]
        model = self.provider.model_name
        dim = self.dimension

        if self.cache is not None:
            cached = self.cache.get(
                chunk_set_id=chunk_set.id, model_name=model, dimension=dim
            )
            if cached is not None:
                cached_ids, vectors = cached
                if cached_ids == ids:
                    return EmbeddedTexts(
                        ids=ids,
                        vectors=vectors,
                        model_name=model,
                        dimension=dim,
                        cache_hit=True,
                    )

        native_dim = self.provider.dimension
        native_vectors: np.ndarray | None = None
        if self.cache is not None and dim != native_dim:
            native_cached = self.cache.get(
                chunk_set_id=chunk_set.id,
                model_name=model,
                dimension=native_dim,
            )
            if native_cached is not None and native_cached[0] == ids:
                native_vectors = native_cached[1]

        if native_vectors is None:
            native_vectors = self.provider.encode(texts)
            if self.cache is not None and dim != native_dim:
                self.cache.set(
                    chunk_set_id=chunk_set.id,
                    model_name=model,
                    dimension=native_dim,
                    ids=ids,
                    vectors=native_vectors,
                )

        vectors = native_vectors
        if dim != native_dim:
            vectors = truncate_vectors(native_vectors, dim)
        if self.cache is not None:
            self.cache.set(
                chunk_set_id=chunk_set.id,
                model_name=model,
                dimension=dim,
                ids=ids,
                vectors=vectors,
            )
        return EmbeddedTexts(
            ids=ids,
            vectors=vectors,
            model_name=model,
            dimension=dim,
            cache_hit=False,
        )

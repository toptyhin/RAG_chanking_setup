"""EmbeddingProvider adapter over remote HTTP embedding clients."""

from __future__ import annotations

import numpy as np

from rageval_embedding_providers.protocol import EmbeddingRemoteProvider


class RemoteEmbeddingProvider:
    """Wraps a remote client that implements ``encode`` into the embedding port."""

    def __init__(self, client: EmbeddingRemoteProvider, *, model_name: str) -> None:
        self._client = client
        self._model_name = model_name
        probe = client.encode(["dimension-probe"])
        if probe.ndim != 2 or probe.shape[0] < 1 or probe.shape[1] < 1:
            raise RuntimeError(
                f"remote embedding probe failed for model {model_name!r}"
            )
        self._dimension = int(probe.shape[1])

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self._dimension), dtype=np.float32)
        vectors = self._client.encode(texts)
        if vectors.ndim != 2 or vectors.shape[0] != len(texts):
            raise RuntimeError(
                f"remote encode returned shape {vectors.shape}, expected "
                f"({len(texts)}, {self._dimension})"
            )
        if vectors.shape[1] != self._dimension:
            raise RuntimeError(
                f"remote encode dim {vectors.shape[1]} != probed {self._dimension}"
            )
        return vectors.astype(np.float32, copy=False)

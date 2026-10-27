"""EmbeddingProvider adapter over remote HTTP embedding clients.

Remote embedding APIs (Ollama ``/api/embed``, OpenAI-compatible ``/embeddings``,
GigaChat) should not receive an entire chunk set in one HTTP request: large
chunk sets exceed client timeouts and lose all progress when one request fails.
This adapter batches ``encode`` calls and retries transport-level failures.
"""

from __future__ import annotations

import logging
import time

import httpx
import numpy as np

from rageval_embedding_providers.protocol import EmbeddingRemoteProvider

logger = logging.getLogger(__name__)

# 32 texts per HTTP request keeps a qwen3-embedding:4b batch well under the
# request timeout while still amortizing per-request overhead.
DEFAULT_BATCH_SIZE = 32
_MAX_ATTEMPTS = 2


class RemoteEmbeddingProvider:
    """Wraps a remote client that implements ``encode`` into the embedding port."""

    def __init__(
        self,
        client: EmbeddingRemoteProvider,
        *,
        model_name: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._client = client
        self._model_name = model_name
        self._batch_size = max(1, int(batch_size))
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

    @property
    def batch_size(self) -> int:
        return self._batch_size

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self._dimension), dtype=np.float32)
        if len(texts) <= self._batch_size:
            return self._encode_with_retry(texts)
        rows: list[np.ndarray] = [
            self._encode_with_retry(texts[start : start + self._batch_size])
            for start in range(0, len(texts), self._batch_size)
        ]
        vectors = np.vstack(rows) if len(rows) > 1 else rows[0]
        if vectors.shape[0] != len(texts):
            raise RuntimeError(
                f"remote encode returned shape {vectors.shape}, expected "
                f"({len(texts)}, {self._dimension})"
            )
        return vectors.astype(np.float32, copy=False)

    def _encode_with_retry(self, batch: list[str]) -> np.ndarray:
        last_exc: httpx.TransportError | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._check_batch(batch, self._client.encode(batch))
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt >= _MAX_ATTEMPTS:
                    raise
                logger.warning(
                    "remote embedding batch of %d text(s) failed (%s); retrying",
                    len(batch),
                    exc,
                )
                time.sleep(min(2.0, 0.5 * attempt))
        assert last_exc is not None
        raise last_exc

    def _check_batch(self, batch: list[str], vectors: np.ndarray) -> np.ndarray:
        if vectors.ndim != 2 or vectors.shape[0] != len(batch):
            raise RuntimeError(
                f"remote encode returned shape {vectors.shape}, expected "
                f"({len(batch)}, {self._dimension})"
            )
        if vectors.shape[1] != self._dimension:
            raise RuntimeError(
                f"remote encode dim {vectors.shape[1]} != probed {self._dimension}"
            )
        return vectors.astype(np.float32, copy=False)

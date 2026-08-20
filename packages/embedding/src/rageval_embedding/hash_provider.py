"""Deterministic embedding provider for tests (no ML deps at runtime)."""

from __future__ import annotations

import hashlib

import numpy as np


class HashEmbeddingProvider:
    """Cheap deterministic vectors; useful in unit tests and CI without GPU."""

    def __init__(self, model_name: str = "hash-emb-v1", dimension: int = 32) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self.encode_calls = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, texts: list[str]) -> np.ndarray:
        self.encode_calls += 1
        rows = []
        for text in texts:
            seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "little")
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(self._dimension).astype(np.float32)
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = vec / norm
            rows.append(vec)
        if not rows:
            return np.zeros((0, self._dimension), dtype=np.float32)
        return np.stack(rows, axis=0)

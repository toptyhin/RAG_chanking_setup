"""Embedding provider port."""

from __future__ import annotations

from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return float32 matrix shape (n, dim), L2-normalized for cosine."""
        ...

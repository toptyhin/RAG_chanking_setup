"""Port for remote / local embedding connection checks."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from rageval_llm_providers.protocol import ConnectionTestResult

__all__ = ["ConnectionTestResult", "EmbeddingRemoteProvider"]


class EmbeddingRemoteProvider(Protocol):
    def list_models(self) -> list[str]: ...

    def ping(self) -> ConnectionTestResult:
        """Cheap connectivity check (list models or tiny embed)."""
        ...

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return float32 matrix shape (n, dim), L2-normalized for cosine."""
        ...

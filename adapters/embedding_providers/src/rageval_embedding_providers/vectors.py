"""Shared vector helpers for remote embedding clients."""

from __future__ import annotations

import numpy as np


def rows_to_normalized_matrix(rows: list[list[float]]) -> np.ndarray:
    """Stack float rows into float32 matrix and L2-normalize each row."""
    if not rows:
        return np.zeros((0, 0), dtype=np.float32)
    vectors = np.asarray(rows, dtype=np.float32)
    if vectors.ndim != 2:
        raise ValueError("embeddings must form a 2-D matrix")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return (vectors / norms).astype(np.float32)

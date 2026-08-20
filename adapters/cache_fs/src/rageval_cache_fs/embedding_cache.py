"""Disk cache for chunk-set embeddings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


class FsEmbeddingCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, chunk_set_id: str, model_name: str, dimension: int) -> Path:
        model_key = hashlib.sha256(model_name.encode()).hexdigest()[:16]
        return self.root / "embeddings" / chunk_set_id / f"{model_key}_d{dimension}"

    def get(
        self, *, chunk_set_id: str, model_name: str, dimension: int
    ) -> tuple[list[str], np.ndarray] | None:
        directory = self._dir(chunk_set_id, model_name, dimension)
        meta_path = directory / "meta.json"
        vec_path = directory / "vectors.npy"
        if not meta_path.is_file() or not vec_path.is_file():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        ids = meta.get("ids")
        if not isinstance(ids, list):
            return None
        vectors = np.load(vec_path, mmap_mode="r")
        if vectors.shape != (len(ids), dimension):
            return None
        return list(ids), vectors.astype(np.float32, copy=False)

    def set(
        self,
        *,
        chunk_set_id: str,
        model_name: str,
        dimension: int,
        ids: list[str],
        vectors: np.ndarray,
    ) -> None:
        directory = self._dir(chunk_set_id, model_name, dimension)
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "vectors.npy", vectors.astype(np.float32, copy=False))
        (directory / "meta.json").write_text(
            json.dumps(
                {
                    "chunk_set_id": chunk_set_id,
                    "model_name": model_name,
                    "dimension": dimension,
                    "ids": ids,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

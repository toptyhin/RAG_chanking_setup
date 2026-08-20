"""Disk cache for SparseBm25Index keyed by chunk_set_id."""

from __future__ import annotations

import logging
from pathlib import Path

from rageval_domain import ChunkSet
from rageval_retrieval import SparseBm25Index

logger = logging.getLogger(__name__)


class FsSparseIndexCache:
    """Load/build BM25 indexes under ``root / sparse / {chunk_set_id}``."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root) / "sparse"

    def path_for(self, chunk_set_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in chunk_set_id)
        return self.root / safe

    def get_or_build(self, chunk_set: ChunkSet) -> SparseBm25Index:
        index_dir = self.path_for(chunk_set.id)
        marker = index_dir / "chunk_ids.json"
        if marker.is_file():
            try:
                return SparseBm25Index.load(index_dir)
            except (OSError, ValueError, KeyError) as exc:
                logger.warning(
                    "corrupt sparse index cache at %s; rebuilding: %s",
                    index_dir,
                    exc,
                )
        return SparseBm25Index.build(chunk_set, index_dir=index_dir)

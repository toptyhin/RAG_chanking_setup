"""Qdrant upload batching without a live server."""

from __future__ import annotations

import numpy as np

from rageval_vectordb_qdrant import QdrantVectorStore


class FakeClient:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    def upsert(self, *, collection_name: str, points: list) -> None:
        assert collection_name == "chunks"
        self.batch_sizes.append(len(points))


def test_upsert_streams_bounded_batches() -> None:
    store = QdrantVectorStore.__new__(QdrantVectorStore)
    store._client = FakeClient()
    store._upsert_batch_size = 256
    store._size_cache = {}
    ids = [f"c{i}" for i in range(600)]
    vectors = np.ones((600, 4), dtype=np.float32)

    store.upsert("chunks", ids, vectors)

    assert store._client.batch_sizes == [256, 256, 88]

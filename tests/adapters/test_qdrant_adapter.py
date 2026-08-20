"""Integration tests against local Qdrant (docker compose)."""

from __future__ import annotations

import uuid

import httpx
import numpy as np
import pytest

from rageval_vectordb_qdrant import QdrantVectorStore

QDRANT_URL = "http://localhost:6333"


def _qdrant_ready() -> bool:
    try:
        response = httpx.get(f"{QDRANT_URL}/readyz", timeout=1.0)
        return response.status_code == 200
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _qdrant_ready(), reason="Qdrant not running on :6333")


def test_qdrant_crud_search() -> None:
    store = QdrantVectorStore(QDRANT_URL)
    name = f"test_{uuid.uuid4().hex[:8]}"
    try:
        store.recreate_collection(name, dimension=4)
        vectors = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        )
        store.upsert(name, ["c1", "c2"], vectors)
        hits = store.search(name, vectors[0], top_k=1)
        assert hits[0].id == "c1"
    finally:
        store.delete_collection(name)


def test_qdrant_quantization_configs_differ() -> None:
    store = QdrantVectorStore(QDRANT_URL)
    none_name = f"test_qnone_{uuid.uuid4().hex[:8]}"
    bin_name = f"test_qbin_{uuid.uuid4().hex[:8]}"
    vectors = np.eye(8, dtype=np.float32)
    ids = [f"c{i}" for i in range(8)]
    try:
        store.recreate_collection(none_name, dimension=8, quantization=None)
        store.upsert(none_name, ids, vectors)
        store.recreate_collection(
            bin_name, dimension=8, quantization={"method": "binary", "rescore": True}
        )
        store.upsert(bin_name, ids, vectors)

        none_info = store.get_collection_info(none_name)
        bin_info = store.get_collection_info(bin_name)
        assert none_info.config.quantization_config is None
        assert bin_info.config.quantization_config is not None

        none_size = store.get_index_size_mb(none_name, dimension=8, quantization=None)
        bin_size = store.get_index_size_mb(
            bin_name, dimension=8, quantization={"method": "binary"}
        )
        assert none_size.index_ram_mb is not None or none_size.source == "unavailable"
        assert bin_size.index_ram_mb is not None or bin_size.source == "unavailable"
        # Configs differ; estimated byte-per-dim also differs when using estimate source.
        if none_size.source == "estimate" and bin_size.source == "estimate":
            assert none_size.index_ram_mb != bin_size.index_ram_mb
    finally:
        store.delete_collection(none_name)
        store.delete_collection(bin_name)

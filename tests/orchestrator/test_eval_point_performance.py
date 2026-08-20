"""Performance invariants for one retrieval point."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rageval_cache_fs import FsEmbeddingCache
from rageval_domain import Chunk, ChunkSet, TestQuery, TestSet
from rageval_embedding import EmbeddingService, HashEmbeddingProvider
from rageval_orchestrator.eval_point import evaluate_retrieval_point
from rageval_retrieval import SparseBm25Index
from rageval_vectordb_qdrant import IndexSizeStats, SearchHit


class FakeVectorStore:
    def __init__(self) -> None:
        self.recreate_calls = 0
        self.upsert_calls = 0
        self.search_calls = 0

    def recreate_collection(self, *args, **kwargs) -> None:
        self.recreate_calls += 1

    def upsert(self, *args, **kwargs) -> None:
        self.upsert_calls += 1

    def search(self, *args, **kwargs) -> list[SearchHit]:
        self.search_calls += 1
        return [SearchHit(id="c1", score=1.0)]

    def get_index_size_mb(self, *args, **kwargs) -> IndexSizeStats:
        return IndexSizeStats(0.25, 0.5, "estimate")


def _fixtures() -> tuple[ChunkSet, TestSet]:
    chunks = ChunkSet(
        id="chunks_perf",
        project_id="proj",
        chunks=[Chunk(chunk_id="c1", doc_id="d1", text="alpha beta")],
    )
    tests = TestSet(
        id="test_perf",
        project_id="proj",
        queries=[
            TestQuery(
                query_id="q1",
                text="alpha",
                relevant_chunk_ids=["c1"],
            )
        ],
    )
    return chunks, tests


@pytest.mark.asyncio
async def test_sparse_point_skips_embedding_and_qdrant(tmp_path: Path) -> None:
    chunk_set, test_set = _fixtures()
    provider = HashEmbeddingProvider(dimension=16)
    embedding = EmbeddingService(provider)
    sparse = SparseBm25Index.build(chunk_set, index_dir=tmp_path / "bm25")
    qdrant = FakeVectorStore()

    metrics, _, _, index_run_id = await evaluate_retrieval_point(
        run_id="run_sparse",
        point_index=0,
        point={"retrieval.mode": "sparse", "retrieval.top_k": 1},
        chunk_set=chunk_set,
        test_set=test_set,
        qdrant=qdrant,  # type: ignore[arg-type]
        embedding=embedding,
        cache=FsEmbeddingCache(tmp_path / "emb"),
        sparse_index=sparse,
    )

    assert provider.encode_calls == 0
    assert qdrant.recreate_calls == 0
    assert qdrant.upsert_calls == 0
    assert index_run_id is None
    assert metrics["index_size_source"] == "bm25_cache"
    assert metrics["index_ram_mb"] > 0


@pytest.mark.asyncio
async def test_search_axes_reuse_index_and_query_embeddings(tmp_path: Path) -> None:
    chunk_set, test_set = _fixtures()
    provider = HashEmbeddingProvider(dimension=16)
    embedding = EmbeddingService(provider)
    qdrant = FakeVectorStore()
    cache = FsEmbeddingCache(tmp_path / "emb")
    index_cache = {}
    query_cache: dict[str, np.ndarray] = {}
    relevance_cache = {}
    persisted: list[str] = []

    async def persist(index_run, chunk_set_id: str) -> str:
        persisted.append(index_run.id)
        return index_run.id

    first = await evaluate_retrieval_point(
        run_id="run_reuse",
        point_index=0,
        point={
            "retrieval.mode": "dense",
            "retrieval.top_k": 1,
            "quantization": "binary",
        },
        chunk_set=chunk_set,
        test_set=test_set,
        qdrant=qdrant,  # type: ignore[arg-type]
        embedding=embedding,
        cache=cache,
        persist_index=persist,
        index_cache=index_cache,
        query_cache=query_cache,
        relevance_cache=relevance_cache,
    )
    second = await evaluate_retrieval_point(
        run_id="run_reuse",
        point_index=1,
        point={
            "retrieval.mode": "dense",
            "retrieval.top_k": 5,
            "quantization": "binary+rescore",
            "retrieval.ef_search": 64,
        },
        chunk_set=chunk_set,
        test_set=test_set,
        qdrant=qdrant,  # type: ignore[arg-type]
        embedding=embedding,
        cache=cache,
        persist_index=persist,
        index_cache=index_cache,
        query_cache=query_cache,
        relevance_cache=relevance_cache,
    )

    assert qdrant.recreate_calls == 1
    assert qdrant.upsert_calls == 1
    assert len(persisted) == 1
    assert first[3] == second[3]
    assert first[0]["index_reused"] is False
    assert second[0]["index_reused"] is True
    # One encode for chunks and one for queries; the second point reuses both.
    assert provider.encode_calls == 2

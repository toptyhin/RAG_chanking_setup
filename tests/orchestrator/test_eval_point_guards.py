"""Stage 52–53 orchestrator eval_point unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rageval_cache_fs import FsEmbeddingCache
from rageval_domain import Chunk, ChunkSet, TestQuery, TestSet
from rageval_embedding import EmbeddingService, HashEmbeddingProvider
from rageval_index import model_collection_tag
from rageval_orchestrator.eval_point import (
    DEFAULT_RERANK_TOP_N,
    _quant_tag,
    _retrieve_depth,
    embedding_for_point,
)
from rageval_rerank import ReverseRerankProvider, rerank_retrieval
from rageval_retrieval.latency import LatencyStats
from rageval_retrieval.results import QueryResult, RetrievalResult


def test_retrieve_depth_funnel_defaults() -> None:
    retrieve_k, top_n, keep, enabled = _retrieve_depth(
        {"rerank.enabled": True, "retrieval.top_k": 10},
        top_k=10,
    )
    assert enabled is True
    assert top_n == DEFAULT_RERANK_TOP_N
    assert keep == 10
    assert retrieve_k == max(10, DEFAULT_RERANK_TOP_N)


def test_retrieve_depth_respects_explicit_top_n_and_candidate_k() -> None:
    retrieve_k, top_n, keep, enabled = _retrieve_depth(
        {
            "rerank.enabled": True,
            "rerank.top_n": 50,
            "rerank.keep": 5,
            "retrieval.top_k": 10,
            "retrieval.candidate_k": 80,
        },
        top_k=10,
    )
    assert enabled is True
    assert top_n == 50
    assert keep == 5
    assert retrieve_k == 80


def test_rerank_funnel_sees_more_than_keep() -> None:
    """Simulate prior retrieval of 50 candidates → keep 5 after reverse rerank."""
    chunks = [
        Chunk(chunk_id=f"c{i}", doc_id="d1", text=f"candidate {i}") for i in range(50)
    ]
    chunk_set = ChunkSet(id="chunks_funnel", project_id="proj", chunks=chunks)
    test_set = TestSet(
        id="test_funnel",
        project_id="proj",
        queries=[TestQuery(query_id="q1", text="q", relevant_chunk_ids=["c49"])],
    )
    prior_ids = [f"c{i}" for i in range(50)]
    prior = RetrievalResult(
        results=[
            QueryResult(
                query_id="q1",
                ranked_chunk_ids=prior_ids,
                scores=[1.0 - i * 0.01 for i in range(50)],
                latency_ms=1.0,
            )
        ],
        latency=LatencyStats(count=1, mean_ms=1.0, p50_ms=1.0, p95_ms=1.0),
    )
    reranked = rerank_retrieval(
        test_set,
        prior,
        chunk_set=chunk_set,
        provider=ReverseRerankProvider(),
        top_n=50,
        keep=5,
    )
    assert len(reranked.results[0].ranked_chunk_ids) == 5
    # Reverse provider promotes last candidates → c49 should be first.
    assert reranked.results[0].ranked_chunk_ids[0] == "c49"


def test_embedding_for_point_rejects_dim_above_provider(tmp_path: Path) -> None:
    provider = HashEmbeddingProvider(dimension=32)
    base = EmbeddingService(provider)
    cache = FsEmbeddingCache(tmp_path / "cache")
    with pytest.raises(ValueError, match="exceeds provider dimension"):
        embedding_for_point({"embedding.dimension": 64}, base, cache)


def test_model_collection_tag_stable_and_distinct() -> None:
    a = model_collection_tag("sentence-transformers/all-MiniLM-L6-v2")
    b = model_collection_tag("BAAI/bge-m3")
    assert a == model_collection_tag("sentence-transformers/all-MiniLM-L6-v2")
    assert a != b
    assert len(a) == 8
    assert a.isalnum()


def test_default_collection_name_includes_model_tag() -> None:
    """Different embedding models must not share a default collection name at same dim."""
    model_a = "hash-emb-v1"
    model_b = "hash-emb-d64"
    tag_a = model_collection_tag(model_a)
    tag_b = model_collection_tag(model_b)
    quant = _quant_tag(None)
    name_a = f"run_r1_0_m{tag_a}_d32_q{quant}"
    name_b = f"run_r1_0_m{tag_b}_d32_q{quant}"
    assert name_a != name_b
    assert f"_m{tag_a}_" in name_a
    assert f"_m{tag_b}_" in name_b

"""Rerank unit tests (no ML dependency)."""

from __future__ import annotations

from rageval_domain import Chunk, ChunkSet, TestQuery, TestSet
from rageval_rerank import ReverseRerankProvider, rerank_retrieval
from rageval_retrieval.results import QueryResult, RetrievalResult
from rageval_retrieval.latency import LatencyStats


def test_rerank_changes_order_and_increases_latency() -> None:
    chunk_set = ChunkSet(
        id="chunks_rr",
        project_id="proj",
        chunks=[
            Chunk(chunk_id="c1", doc_id="d1", text="first candidate"),
            Chunk(chunk_id="c2", doc_id="d1", text="second candidate"),
            Chunk(chunk_id="c3", doc_id="d1", text="third candidate"),
        ],
    )
    test_set = TestSet(
        id="test_rr",
        project_id="proj",
        queries=[TestQuery(query_id="q1", text="query", relevant_chunk_ids=["c3"])],
    )
    prior = RetrievalResult(
        results=[
            QueryResult(
                query_id="q1",
                ranked_chunk_ids=["c1", "c2", "c3"],
                scores=[0.9, 0.8, 0.1],
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
        keep=3,
    )
    assert reranked.results[0].ranked_chunk_ids == ["c3", "c2", "c1"]
    assert reranked.latency.p50_ms > prior.latency.p50_ms

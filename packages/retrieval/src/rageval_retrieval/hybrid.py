"""Hybrid dense + sparse retrieval with RRF or weighted fusion."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

from rageval_domain import TestSet
from rageval_embedding.service import EmbeddingService
from rageval_retrieval.dense import QueryEmbeddingCache, dense_retrieve
from rageval_retrieval.latency import summarize_latencies
from rageval_retrieval.results import QueryResult, RetrievalResult
from rageval_retrieval.sparse import SparseBm25Index, sparse_retrieve
from rageval_vectordb_qdrant import QdrantVectorStore


@dataclass(slots=True)
class HybridRetrieveOptions:
    """Optional fusion / search knobs for hybrid retrieval."""

    top_k: int = 10
    candidate_k: int | None = None
    rrf_k: int = 60
    fusion: str = "rrf"
    dense_weight: float = 0.5
    rescore: bool | None = None
    ef_search: int | None = None
    query_cache: QueryEmbeddingCache | None = None


def rrf_fuse(
    rankings: Iterable[list[str]],
    *,
    top_k: int,
    k: int = 60,
) -> tuple[list[str], list[float]]:
    """Fuse ranked id lists with classic RRF: score = Σ 1/(k + rank)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    return [doc_id for doc_id, _ in ordered], [score for _, score in ordered]


def _normalize_scores(ids: list[str], scores: list[float]) -> dict[str, float]:
    if not ids:
        return {}
    if not scores or len(scores) != len(ids):
        n = len(ids)
        return {doc_id: (n - i) / n for i, doc_id in enumerate(ids)}
    lo = min(scores)
    hi = max(scores)
    if hi <= lo:
        return {doc_id: 1.0 for doc_id in ids}
    span = hi - lo
    return {doc_id: (s - lo) / span for doc_id, s in zip(ids, scores, strict=True)}


def weighted_fuse(
    dense_ids: list[str],
    dense_scores: list[float],
    sparse_ids: list[str],
    sparse_scores: list[float],
    *,
    top_k: int,
    dense_weight: float = 0.5,
) -> tuple[list[str], list[float]]:
    """Linear fusion of min-max normalized dense/sparse scores."""
    w_d = max(0.0, min(1.0, dense_weight))
    w_s = 1.0 - w_d
    d_norm = _normalize_scores(dense_ids, dense_scores)
    s_norm = _normalize_scores(sparse_ids, sparse_scores)
    all_ids = set(d_norm) | set(s_norm)
    combined = {
        doc_id: w_d * d_norm.get(doc_id, 0.0) + w_s * s_norm.get(doc_id, 0.0)
        for doc_id in all_ids
    }
    ordered = sorted(combined.items(), key=lambda item: item[1], reverse=True)[:top_k]
    return [doc_id for doc_id, _ in ordered], [score for _, score in ordered]


def hybrid_retrieve(
    test_set: TestSet,
    *,
    collection_name: str,
    embedding: EmbeddingService,
    store: QdrantVectorStore,
    sparse_index: SparseBm25Index,
    options: HybridRetrieveOptions | None = None,
) -> RetrievalResult:
    """Run dense + sparse, fuse with RRF or weighted scores."""
    opts = options or HybridRetrieveOptions()
    top_k = opts.top_k
    cand_k = opts.candidate_k or max(top_k * 2, top_k)
    dense = dense_retrieve(
        test_set,
        collection_name=collection_name,
        embedding=embedding,
        store=store,
        top_k=cand_k,
        rescore=opts.rescore,
        ef_search=opts.ef_search,
        query_cache=opts.query_cache,
    )
    sparse = sparse_retrieve(test_set, index=sparse_index, top_k=cand_k)

    dense_by_q = {r.query_id: r for r in dense.results}
    sparse_by_q = {r.query_id: r for r in sparse.results}
    fusion_mode = opts.fusion.lower().strip()

    query_results: list[QueryResult] = []
    latencies: list[float] = []
    for query in test_set.queries:
        started = time.perf_counter()
        dense_ids = dense_by_q.get(query.query_id)
        sparse_ids = sparse_by_q.get(query.query_id)
        d_ranked = dense_ids.ranked_chunk_ids if dense_ids else []
        s_ranked = sparse_ids.ranked_chunk_ids if sparse_ids else []
        d_scores = dense_ids.scores if dense_ids else []
        s_scores = sparse_ids.scores if sparse_ids else []

        if fusion_mode == "weighted":
            fused_ids, fused_scores = weighted_fuse(
                d_ranked,
                d_scores,
                s_ranked,
                s_scores,
                top_k=top_k,
                dense_weight=opts.dense_weight,
            )
        else:
            fused_ids, fused_scores = rrf_fuse(
                [d_ranked, s_ranked], top_k=top_k, k=opts.rrf_k
            )

        upstream_ms = 0.0
        if dense_ids is not None:
            upstream_ms = max(upstream_ms, dense_ids.latency_ms)
        if sparse_ids is not None:
            upstream_ms = max(upstream_ms, sparse_ids.latency_ms)
        latency_ms = upstream_ms + (time.perf_counter() - started) * 1000.0
        latencies.append(latency_ms)
        query_results.append(
            QueryResult(
                query_id=query.query_id,
                ranked_chunk_ids=fused_ids,
                scores=fused_scores,
                latency_ms=latency_ms,
            )
        )

    return RetrievalResult(results=query_results, latency=summarize_latencies(latencies))

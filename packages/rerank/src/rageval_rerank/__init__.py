"""Cross-encoder reranking over retrieval candidates."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from rageval_domain import ChunkSet, TestSet
from rageval_retrieval.latency import LatencyStats, summarize_latencies
from rageval_retrieval.results import QueryResult, RetrievalResult

DEFAULT_CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass(slots=True)
class RerankCandidate:
    chunk_id: str
    text: str
    score: float = 0.0


class RerankProvider(Protocol):
    def score(self, query: str, candidates: list[RerankCandidate]) -> list[float]:
        """Return one score per candidate (higher is better)."""
        ...


class ReverseRerankProvider:
    """Deterministic test double: reverses order and adds tiny delay."""

    def score(self, query: str, candidates: list[RerankCandidate]) -> list[float]:
        time.sleep(0.001)
        # Later candidates get higher scores → sorted order reverses.
        return [float(i) for i in range(len(candidates))]


class CrossEncoderRerankProvider:
    """Local sentence-transformers CrossEncoder (optional ML extra)."""

    def __init__(self, model_name: str = DEFAULT_CROSS_ENCODER) -> None:
        from sentence_transformers import CrossEncoder

        self.model_name = model_name
        self._model = CrossEncoder(model_name)

    def score(self, query: str, candidates: list[RerankCandidate]) -> list[float]:
        if not candidates:
            return []
        pairs = [(query, c.text) for c in candidates]
        raw = self._model.predict(pairs, show_progress_bar=False)
        return [float(x) for x in raw]


def rerank_retrieval(
    test_set: TestSet,
    retrieval: RetrievalResult,
    *,
    chunk_set: ChunkSet,
    provider: RerankProvider,
    top_n: int | None = None,
    keep: int | None = None,
) -> RetrievalResult:
    """Re-score top_n candidates per query and keep top `keep` (default: same length)."""
    texts = {c.chunk_id: c.text for c in chunk_set.chunks}
    query_results: list[QueryResult] = []
    latencies: list[float] = []

    for query, prior in zip(test_set.queries, retrieval.results, strict=False):
        if prior.query_id != query.query_id:
            prior = next(r for r in retrieval.results if r.query_id == query.query_id)
        ranked = prior.ranked_chunk_ids
        if top_n is not None:
            ranked = ranked[:top_n]
        keep_n = keep if keep is not None else len(ranked)
        candidates = [
            RerankCandidate(chunk_id=cid, text=texts.get(cid, ""), score=0.0)
            for cid in ranked
            if cid in texts
        ]
        started = time.perf_counter()
        scores = provider.score(query.text, candidates) if candidates else []
        latency_ms = prior.latency_ms + (time.perf_counter() - started) * 1000.0
        latencies.append(latency_ms)
        scored = sorted(
            zip(candidates, scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )[:keep_n]
        query_results.append(
            QueryResult(
                query_id=query.query_id,
                ranked_chunk_ids=[c.chunk_id for c, _ in scored],
                scores=[float(s) for _, s in scored],
                latency_ms=latency_ms,
            )
        )

    return RetrievalResult(
        results=query_results,
        latency=summarize_latencies(latencies),
    )


__all__ = [
    "DEFAULT_CROSS_ENCODER",
    "CrossEncoderRerankProvider",
    "LatencyStats",
    "RerankCandidate",
    "RerankProvider",
    "ReverseRerankProvider",
    "rerank_retrieval",
]

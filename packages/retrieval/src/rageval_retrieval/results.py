"""Shared retrieval result types."""

from __future__ import annotations

from dataclasses import dataclass, field

from rageval_retrieval.latency import LatencyStats


@dataclass(slots=True)
class QueryResult:
    query_id: str
    ranked_chunk_ids: list[str]
    scores: list[float]
    latency_ms: float


@dataclass
class RetrievalResult:
    results: list[QueryResult] = field(default_factory=list)
    latency: LatencyStats = field(
        default_factory=lambda: LatencyStats(0, 0.0, 0.0, 0.0)
    )

    def ranked_lists(self) -> dict[str, list[str]]:
        return {r.query_id: r.ranked_chunk_ids for r in self.results}


# Backward-compatible alias used by dense retrieval callers.
DenseRetrievalResult = RetrievalResult

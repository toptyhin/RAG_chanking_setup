"""Sparse BM25 retrieval over a ChunkSet (bm25s)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import bm25s

from rageval_domain import ChunkSet, TestSet
from rageval_retrieval.latency import summarize_latencies
from rageval_retrieval.results import QueryResult, RetrievalResult

_CHUNK_IDS_NAME = "chunk_ids.json"


@dataclass(slots=True)
class SparseBm25Index:
    """In-memory (optionally on-disk) BM25 index keyed by chunk_id."""

    chunk_ids: list[str]
    retriever: bm25s.BM25
    index_dir: Path | None = None

    @classmethod
    def build(cls, chunk_set: ChunkSet, *, index_dir: Path | None = None) -> SparseBm25Index:
        chunk_ids = [c.chunk_id for c in chunk_set.chunks]
        texts = [c.text for c in chunk_set.chunks]
        tokens = bm25s.tokenize(texts, show_progress=False)
        retriever = bm25s.BM25()
        retriever.index(tokens, show_progress=False)
        index = cls(chunk_ids=chunk_ids, retriever=retriever, index_dir=index_dir)
        if index_dir is not None:
            index.save(index_dir)
        return index

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        self.retriever.save(str(index_dir), show_progress=False)
        (index_dir / _CHUNK_IDS_NAME).write_text(
            json.dumps(self.chunk_ids, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, index_dir: Path) -> SparseBm25Index:
        chunk_ids = json.loads((index_dir / _CHUNK_IDS_NAME).read_text(encoding="utf-8"))
        retriever = bm25s.BM25.load(str(index_dir), load_corpus=False)
        return cls(chunk_ids=list(chunk_ids), retriever=retriever, index_dir=index_dir)

    def size_mb(self) -> float | None:
        """Return persisted BM25 cache size without querying Qdrant telemetry."""
        if self.index_dir is None or not self.index_dir.is_dir():
            return None
        total = sum(path.stat().st_size for path in self.index_dir.rglob("*") if path.is_file())
        return total / (1024.0 * 1024.0)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if not self.chunk_ids or top_k <= 0:
            return []
        k = min(top_k, len(self.chunk_ids))
        query_tokens = bm25s.tokenize([query], show_progress=False)
        results = self.retriever.retrieve(query_tokens, k=k, show_progress=False)
        hits: list[tuple[str, float]] = []
        for doc_idx, score in zip(results.documents[0], results.scores[0], strict=True):
            idx = int(doc_idx)
            if idx < 0 or idx >= len(self.chunk_ids):
                continue
            hits.append((self.chunk_ids[idx], float(score)))
        return hits


def sparse_retrieve(
    test_set: TestSet,
    *,
    index: SparseBm25Index,
    top_k: int = 10,
) -> RetrievalResult:
    query_results: list[QueryResult] = []
    latencies: list[float] = []

    for query in test_set.queries:
        started = time.perf_counter()
        hits = index.search(query.text, top_k=top_k)
        latency_ms = (time.perf_counter() - started) * 1000.0
        latencies.append(latency_ms)
        query_results.append(
            QueryResult(
                query_id=query.query_id,
                ranked_chunk_ids=[h[0] for h in hits],
                scores=[h[1] for h in hits],
                latency_ms=latency_ms,
            )
        )

    return RetrievalResult(
        results=query_results,
        latency=summarize_latencies(latencies),
    )

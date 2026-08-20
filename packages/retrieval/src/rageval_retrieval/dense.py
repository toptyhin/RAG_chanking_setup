"""Dense retrieval over an IndexRun collection."""

from __future__ import annotations

import hashlib
import json
import time

import numpy as np

from rageval_domain import TestSet
from rageval_embedding.service import EmbeddingService
from rageval_retrieval.latency import summarize_latencies
from rageval_retrieval.results import DenseRetrievalResult, QueryResult, RetrievalResult
from rageval_vectordb_qdrant import QdrantVectorStore

__all__ = ["DenseRetrievalResult", "QueryResult", "RetrievalResult", "dense_retrieve"]

QueryEmbeddingCache = dict[str, np.ndarray]


def _query_embedding_key(test_set: TestSet, embedding: EmbeddingService) -> str:
    payload = {
        "queries": [(query.query_id, query.text) for query in test_set.queries],
        "model": embedding.provider.model_name,
        "dimension": embedding.dimension,
        "normalize": bool(getattr(embedding.provider, "normalize", True)),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def dense_retrieve(
    test_set: TestSet,
    *,
    collection_name: str,
    embedding: EmbeddingService,
    store: QdrantVectorStore,
    top_k: int = 10,
    rescore: bool | None = None,
    ef_search: int | None = None,
    query_cache: QueryEmbeddingCache | None = None,
) -> RetrievalResult:
    texts = [q.text for q in test_set.queries]
    cache_key = _query_embedding_key(test_set, embedding)
    vectors = query_cache.get(cache_key) if query_cache is not None else None
    if vectors is None:
        vectors = embedding.embed_texts(texts)
        if query_cache is not None:
            query_cache[cache_key] = vectors
    query_results: list[QueryResult] = []
    latencies: list[float] = []

    for i, query in enumerate(test_set.queries):
        started = time.perf_counter()
        hits = store.search(
            collection_name,
            vectors[i],
            top_k=top_k,
            rescore=rescore,
            ef_search=ef_search,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        latencies.append(latency_ms)
        query_results.append(
            QueryResult(
                query_id=query.query_id,
                ranked_chunk_ids=[h.id for h in hits],
                scores=[h.score for h in hits],
                latency_ms=latency_ms,
            )
        )

    return RetrievalResult(
        results=query_results,
        latency=summarize_latencies(latencies),
    )

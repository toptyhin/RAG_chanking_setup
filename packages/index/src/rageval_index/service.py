"""Build a Qdrant index from a ChunkSet + embeddings."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from rageval_domain import ChunkSet, IndexRun
from rageval_embedding.service import EmbeddingService
from rageval_vectordb_qdrant import QdrantVectorStore, parse_quantization_axis


@dataclass(slots=True)
class IndexBuildResult:
    index_run: IndexRun
    collection_name: str
    cache_hit: bool
    build_time_sec: float
    vector_count: int
    rescore: bool | None = None


def model_collection_tag(model_name: str) -> str:
    """Short stable tag so different embedding models never share a collection name."""
    return hashlib.sha256(model_name.encode()).hexdigest()[:8]


def build_index(
    chunk_set: ChunkSet,
    *,
    embedding: EmbeddingService,
    store: QdrantVectorStore,
    collection_name: str | None = None,
    quantization: Any = None,
    hnsw: dict[str, Any] | None = None,
) -> IndexBuildResult:
    quant_config, rescore = parse_quantization_axis(quantization)
    hnsw_config = dict(hnsw) if hnsw else {}
    started = time.perf_counter()
    embedded = embedding.embed_chunk_set(chunk_set)
    model_tag = model_collection_tag(embedded.model_name)
    name = collection_name or f"idx_{chunk_set.id}_m{model_tag}_d{embedded.dimension}"
    # Qdrant collection names: keep alphanumeric + underscore
    name = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)[:200]

    store.recreate_collection(
        name,
        embedded.dimension,
        quantization=quant_config,
        hnsw=hnsw_config or None,
    )
    payloads = [{"doc_id": c.doc_id} for c in chunk_set.chunks]
    store.upsert(name, embedded.ids, embedded.vectors, payloads=payloads)
    build_time = time.perf_counter() - started

    index_run = IndexRun(
        project_id=chunk_set.project_id,
        parent_ids=[chunk_set.id],
        chunk_set_id=chunk_set.id,
        collection_name=name,
        embedding_model=embedded.model_name,
        dimension=embedded.dimension,
        quantization=quant_config,
        hnsw=hnsw_config,
        build_time_sec=build_time,
        meta={
            "vector_count": len(embedded.ids),
            "cache_hit": embedded.cache_hit,
            "rescore": rescore,
        },
    )
    return IndexBuildResult(
        index_run=index_run,
        collection_name=name,
        cache_hit=embedded.cache_hit,
        build_time_sec=build_time,
        vector_count=len(embedded.ids),
        rescore=rescore,
    )

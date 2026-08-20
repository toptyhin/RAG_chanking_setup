"""Shared embed→index→retrieve→score path for one config point."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Callable

from rageval_cache_fs import FsEmbeddingCache
from rageval_domain import ChunkSet, TestSet
from rageval_embedding import EmbeddingService
from rageval_eval import (
    RelevanceIndex,
    answer_coverage_at_k,
    build_relevance_index,
    mean_metric,
    resolve_relevance,
    resolve_relevance_grades,
    score_retrieval,
)
from rageval_index import IndexBuildResult, build_index, model_collection_tag
from rageval_rerank import (
    DEFAULT_CROSS_ENCODER,
    ReverseRerankProvider,
    RerankProvider,
    rerank_retrieval,
)
from rageval_retrieval import (
    HybridRetrieveOptions,
    QueryEmbeddingCache,
    SparseBm25Index,
    dense_retrieve,
    hybrid_retrieve,
    sparse_retrieve,
)
from rageval_vectordb_qdrant import (
    IndexSizeStats,
    QdrantVectorStore,
    parse_quantization_axis,
)

ResolveEmbedding = Callable[[str], EmbeddingService]
ResolveRerank = Callable[[str], RerankProvider]
EnsureEmbedding = Callable[[str], Awaitable[EmbeddingService]]
EnsureRerank = Callable[[str], Awaitable[RerankProvider]]
RelevanceData = tuple[
    RelevanceIndex,
    dict[str, list[str]],
    dict[str, dict[str, float]],
]


@dataclass(slots=True)
class ReusedIndex:
    build: IndexBuildResult
    index_run_id: str
    size: IndexSizeStats


IndexReuseCache = dict[tuple[Any, ...], ReusedIndex]
RelevanceCache = dict[str, RelevanceData]

# Default rerank funnel depth when rerank.enabled and rerank.top_n omitted.
DEFAULT_RERANK_TOP_N = 50


@dataclass(slots=True)
class EvalPointDeps:
    """Runtime dependencies for one retrieval config evaluation."""

    run_id: str
    point_index: int
    point: dict[str, Any]
    chunk_set: ChunkSet
    test_set: TestSet
    qdrant: QdrantVectorStore
    embedding: EmbeddingService
    cache: FsEmbeddingCache
    sparse_index: SparseBm25Index | None = None
    persist_index: Callable[..., Any] | None = None
    rerank_provider: Any | None = None
    resolve_embedding: ResolveEmbedding | None = None
    resolve_rerank: ResolveRerank | None = None
    ensure_embedding: EnsureEmbedding | None = None
    ensure_rerank: EnsureRerank | None = None
    index_cache: IndexReuseCache | None = None
    query_cache: QueryEmbeddingCache | None = None
    relevance_cache: RelevanceCache | None = None


def _quant_tag(quantization: Any) -> str:
    config, _ = parse_quantization_axis(quantization)
    if config is None:
        return "none"
    return str(config.get("method", "none"))


def _quant_build_config(quantization: Any) -> dict[str, Any] | None:
    config, _ = parse_quantization_axis(quantization)
    if config is None:
        return None
    return {
        key: value
        for key, value in config.items()
        if key not in {"rescore", "enabled"}
    }


def _hnsw_from_point(point: dict[str, Any]) -> dict[str, Any]:
    """Collect HNSW build params from point axes."""
    hnsw: dict[str, Any] = {}
    if "index.hnsw.m" in point:
        hnsw["m"] = int(point["index.hnsw.m"])
    if "index.hnsw.ef_construct" in point:
        hnsw["ef_construct"] = int(point["index.hnsw.ef_construct"])
    nested = point.get("index.hnsw")
    if isinstance(nested, dict):
        if "m" in nested:
            hnsw["m"] = int(nested["m"])
        if "ef_construct" in nested:
            hnsw["ef_construct"] = int(nested["ef_construct"])
    return hnsw


def index_group_key(
    point: dict[str, Any],
    *,
    chunk_set_id: str,
    default_model: str,
    default_dimension: int,
) -> tuple[Any, ...]:
    """Group points by index-build inputs; search-only axes are intentionally absent."""
    mode = str(point.get("retrieval.mode", "dense")).lower()
    if mode == "sparse":
        return ("sparse", chunk_set_id)
    quant_raw = point.get("quantization", point.get("index.quantization"))
    return (
        "dense",
        chunk_set_id,
        str(point.get("embedding.model", default_model)),
        int(point.get("embedding.dimension", default_dimension)),
        json.dumps(_quant_build_config(quant_raw), sort_keys=True),
        json.dumps(_hnsw_from_point(point), sort_keys=True),
        point.get("index.collection_name"),
    )


def embedding_for_point(
    point: dict[str, Any],
    base: EmbeddingService,
    cache: FsEmbeddingCache,
    *,
    resolve_embedding: ResolveEmbedding | None = None,
) -> EmbeddingService:
    if "embedding.model" in point and resolve_embedding is not None:
        base = resolve_embedding(str(point["embedding.model"]))

    if "embedding.dimension" not in point:
        if base.cache is cache:
            return base
        target = None if base.dimension == base.provider.dimension else base.dimension
        return EmbeddingService(base.provider, cache=cache, dimension=target)

    dim = int(point["embedding.dimension"])
    if dim > base.provider.dimension:
        raise ValueError(
            f"embedding.dimension {dim} exceeds provider dimension "
            f"{base.provider.dimension} for model {base.provider.model_name!r}; "
            f"MRL truncate only supports dim <= native size"
        )
    return EmbeddingService(base.provider, cache=cache, dimension=dim)


def rerank_for_point(
    point: dict[str, Any],
    *,
    injected: RerankProvider | None = None,
    resolve_rerank: ResolveRerank | None = None,
) -> RerankProvider:
    provider_name = str(point.get("rerank.provider", "")).lower().strip()
    if provider_name in {"reverse", "test"}:
        return ReverseRerankProvider()
    if injected is not None and "rerank.model" not in point and not provider_name:
        return injected
    model_id = str(point.get("rerank.model") or DEFAULT_CROSS_ENCODER)
    if resolve_rerank is not None:
        return resolve_rerank(model_id)
    return ReverseRerankProvider()


def _retrieve_depth(point: dict[str, Any], top_k: int) -> tuple[int, int, int, bool]:
    """Return (retrieve_k, rerank_top_n, rerank_keep, rerank_enabled)."""
    rerank_enabled = bool(point.get("rerank.enabled", False))
    keep = int(point.get("rerank.keep", top_k))
    top_n = int(point.get("rerank.top_n", DEFAULT_RERANK_TOP_N))
    retrieve_k = top_k
    if rerank_enabled:
        retrieve_k = max(retrieve_k, top_n)
    if "retrieval.candidate_k" in point and point["retrieval.candidate_k"] is not None:
        retrieve_k = max(retrieve_k, int(point["retrieval.candidate_k"]))
    return retrieve_k, top_n, keep, rerank_enabled


def _collection_name_for(
    *,
    run_id: str,
    point: dict[str, Any],
    build_key: tuple[Any, ...],
    model_name: str,
    dim: int,
    quant_raw: Any,
    hnsw: dict[str, Any],
) -> str:
    collection_name = point.get("index.collection_name")
    if collection_name is not None:
        return str(collection_name)
    model_tag = model_collection_tag(model_name)
    quant_part = _quant_tag(quant_raw)
    hnsw_part = ""
    if hnsw:
        hnsw_part = f"_hnswm{hnsw.get('m', 'd')}_efc{hnsw.get('ef_construct', 'd')}"
    key_tag = hashlib.sha256(repr(build_key).encode()).hexdigest()[:10]
    return f"run_{run_id}_{key_tag}_m{model_tag}_d{dim}_q{quant_part}{hnsw_part}"


async def _ensure_dense_index(
    deps: EvalPointDeps,
    *,
    quant_raw: Any,
    hnsw: dict[str, Any],
) -> tuple[ReusedIndex, EmbeddingService, bool]:
    point = deps.point
    base_embedding = deps.embedding
    model_id = point.get("embedding.model")
    if model_id is not None and deps.ensure_embedding is not None:
        base_embedding = await deps.ensure_embedding(str(model_id))
    point_embedding = embedding_for_point(
        point,
        base_embedding,
        deps.cache,
        resolve_embedding=deps.resolve_embedding if deps.ensure_embedding is None else None,
    )
    dim = point_embedding.dimension
    build_key = index_group_key(
        point,
        chunk_set_id=deps.chunk_set.id,
        default_model=point_embedding.provider.model_name,
        default_dimension=dim,
    )
    active_index_cache = deps.index_cache if deps.index_cache is not None else {}
    reused = active_index_cache.get(build_key)
    if reused is not None:
        return reused, point_embedding, True

    collection_name = _collection_name_for(
        run_id=deps.run_id,
        point=point,
        build_key=build_key,
        model_name=point_embedding.provider.model_name,
        dim=dim,
        quant_raw=quant_raw,
        hnsw=hnsw,
    )
    build = await asyncio.to_thread(
        build_index,
        deps.chunk_set,
        embedding=point_embedding,
        store=deps.qdrant,
        collection_name=collection_name,
        quantization=_quant_build_config(quant_raw),
        hnsw=hnsw or None,
    )
    index_run_id = build.index_run.id
    if deps.persist_index is not None:
        index_run_id = await deps.persist_index(build.index_run, deps.chunk_set.id)
    size = await asyncio.to_thread(
        deps.qdrant.get_index_size_mb,
        build.collection_name,
        dimension=dim,
        quantization=_quant_build_config(quant_raw),
    )
    reused = ReusedIndex(build=build, index_run_id=index_run_id, size=size)
    active_index_cache[build_key] = reused
    return reused, point_embedding, False


async def _run_retrieval(
    deps: EvalPointDeps,
    *,
    mode: str,
    retrieve_k: int,
    build: IndexBuildResult | None,
    point_embedding: EmbeddingService | None,
    search_rescore: bool | None,
    ef_search_int: int | None,
) -> Any:
    point = deps.point
    hybrid_candidate_k = point.get("retrieval.candidate_k")
    if hybrid_candidate_k is None:
        hybrid_candidate_k = max(retrieve_k * 2, retrieve_k)
    else:
        hybrid_candidate_k = int(hybrid_candidate_k)

    if mode == "dense":
        assert build is not None and point_embedding is not None
        return await asyncio.to_thread(
            dense_retrieve,
            deps.test_set,
            collection_name=build.collection_name,
            embedding=point_embedding,
            store=deps.qdrant,
            top_k=retrieve_k,
            rescore=search_rescore,
            ef_search=ef_search_int,
            query_cache=deps.query_cache,
        )
    if mode == "sparse":
        assert deps.sparse_index is not None
        return await asyncio.to_thread(
            sparse_retrieve,
            deps.test_set,
            index=deps.sparse_index,
            top_k=retrieve_k,
        )
    if mode == "hybrid":
        assert (
            deps.sparse_index is not None
            and build is not None
            and point_embedding is not None
        )
        options = HybridRetrieveOptions(
            top_k=retrieve_k,
            candidate_k=hybrid_candidate_k,
            rrf_k=int(point.get("retrieval.hybrid.rrf_k", 60)),
            fusion=str(point.get("retrieval.hybrid.fusion", "rrf")).lower(),
            dense_weight=float(point.get("retrieval.hybrid.dense_weight", 0.5)),
            rescore=search_rescore,
            ef_search=ef_search_int,
            query_cache=deps.query_cache,
        )
        return await asyncio.to_thread(
            hybrid_retrieve,
            deps.test_set,
            collection_name=build.collection_name,
            embedding=point_embedding,
            store=deps.qdrant,
            sparse_index=deps.sparse_index,
            options=options,
        )
    raise ValueError(f"unsupported retrieval.mode: {mode!r}")


async def _maybe_rerank(
    deps: EvalPointDeps,
    retrieval: Any,
    *,
    rerank_enabled: bool,
    rerank_top_n: int,
    rerank_keep: int,
) -> Any:
    if not rerank_enabled:
        return retrieval
    point = deps.point
    model_id = str(point.get("rerank.model") or DEFAULT_CROSS_ENCODER)
    if deps.ensure_rerank is not None and str(
        point.get("rerank.provider", "")
    ).lower() not in {"reverse", "test"}:
        provider = await deps.ensure_rerank(model_id)
    else:
        provider = rerank_for_point(
            point,
            injected=deps.rerank_provider,
            resolve_rerank=deps.resolve_rerank,
        )
    return await asyncio.to_thread(
        rerank_retrieval,
        deps.test_set,
        retrieval,
        chunk_set=deps.chunk_set,
        provider=provider,
        top_n=rerank_top_n,
        keep=rerank_keep,
    )


def _relevance_for_chunk_set(
    deps: EvalPointDeps,
) -> tuple[dict[str, list[str]], dict[str, dict[str, float]]]:
    relevance_data = (
        deps.relevance_cache.get(deps.chunk_set.id)
        if deps.relevance_cache is not None
        else None
    )
    if relevance_data is None:
        relevance_index = build_relevance_index(deps.chunk_set)
        relevance = resolve_relevance(
            deps.test_set,
            deps.chunk_set,
            index=relevance_index,
        )
        grades = resolve_relevance_grades(
            deps.test_set,
            deps.chunk_set,
            relevance=relevance,
            index=relevance_index,
        )
        relevance_data = (relevance_index, relevance, grades)
        if deps.relevance_cache is not None:
            deps.relevance_cache[deps.chunk_set.id] = relevance_data
    _, relevance, grades = relevance_data
    return relevance, grades


def _enrich_metrics(
    *,
    metrics: dict[str, Any],
    build: IndexBuildResult | None,
    index_reused: bool,
    mode: str,
    quant_config: Any,
    retrieve_k: int,
    rerank_enabled: bool,
    rerank_top_n: int,
    rerank_keep: int,
    hnsw: dict[str, Any],
    ef_search_int: int | None,
    retrieval: Any,
    test_set: TestSet,
    chunk_set: ChunkSet,
    reused: ReusedIndex | None,
    sparse_index: SparseBm25Index | None,
) -> str | None:
    metrics["cache_hit"] = build.cache_hit if build is not None else True
    metrics["build_time_sec"] = build.build_time_sec if build is not None else 0.0
    metrics["vector_count"] = build.vector_count if build is not None else 0
    metrics["index_reused"] = index_reused
    metrics["retrieval.mode"] = mode
    metrics["quantization"] = quant_config
    metrics["retrieve_k"] = retrieve_k
    if rerank_enabled:
        metrics["rerank.top_n"] = rerank_top_n
        metrics["rerank.keep"] = rerank_keep
    if hnsw:
        metrics["hnsw"] = hnsw
    if ef_search_int is not None:
        metrics["ef_search"] = ef_search_int

    chunk_texts = {c.chunk_id: c.text for c in chunk_set.chunks}
    ranked = retrieval.ranked_lists()
    for k in (1, 5, 10):
        coverages: list[float] = []
        for query in test_set.queries:
            expected = query.expected_answer or query.source_quote
            if not expected:
                continue
            top_ids = ranked.get(query.query_id, [])[:k]
            texts = [chunk_texts.get(cid, "") for cid in top_ids]
            coverages.append(answer_coverage_at_k(expected, texts))
        if coverages:
            metrics[f"answer_coverage@{k}"] = mean_metric(coverages)

    if reused is not None:
        metrics["index_ram_mb"] = reused.size.index_ram_mb
        metrics["index_disk_mb"] = reused.size.index_disk_mb
        metrics["index_size_source"] = reused.size.source
        return reused.index_run_id

    sparse_mb = sparse_index.size_mb() if sparse_index is not None else None
    metrics["index_ram_mb"] = sparse_mb
    metrics["index_disk_mb"] = sparse_mb
    metrics["index_size_source"] = "bm25_cache" if sparse_mb is not None else "unavailable"
    return None


async def _evaluate_with_deps(
    deps: EvalPointDeps,
) -> tuple[dict[str, Any], float | None, float | None, str | None]:
    point = deps.point
    top_k = int(point.get("retrieval.top_k", 10))
    retrieve_k, rerank_top_n, rerank_keep, rerank_enabled = _retrieve_depth(point, top_k)
    mode = str(point.get("retrieval.mode", "dense")).lower()
    quant_raw = point.get("quantization", point.get("index.quantization"))
    quant_config, rescore = parse_quantization_axis(quant_raw)
    hnsw = _hnsw_from_point(point)
    ef_search = point.get("retrieval.ef_search")
    ef_search_int = int(ef_search) if ef_search is not None else None

    if deps.sparse_index is None and mode in {"sparse", "hybrid"}:
        deps.sparse_index = await asyncio.to_thread(SparseBm25Index.build, deps.chunk_set)

    point_embedding: EmbeddingService | None = None
    reused: ReusedIndex | None = None
    index_reused = False
    if mode != "sparse":
        reused, point_embedding, index_reused = await _ensure_dense_index(
            deps, quant_raw=quant_raw, hnsw=hnsw
        )

    build = reused.build if reused is not None else None
    search_rescore = rescore if rescore is not None else (build.rescore if build else None)
    retrieval = await _run_retrieval(
        deps,
        mode=mode,
        retrieve_k=retrieve_k,
        build=build,
        point_embedding=point_embedding,
        search_rescore=search_rescore,
        ef_search_int=ef_search_int,
    )
    retrieval = await _maybe_rerank(
        deps,
        retrieval,
        rerank_enabled=rerank_enabled,
        rerank_top_n=rerank_top_n,
        rerank_keep=rerank_keep,
    )
    relevance, grades = _relevance_for_chunk_set(deps)
    metrics = score_retrieval(
        relevance,
        retrieval.ranked_lists(),
        ks=(1, 5, 10),
        grades_by_query=grades,
        test_set=deps.test_set,
    )
    index_run_id = _enrich_metrics(
        metrics=metrics,
        build=build,
        index_reused=index_reused,
        mode=mode,
        quant_config=quant_config,
        retrieve_k=retrieve_k,
        rerank_enabled=rerank_enabled,
        rerank_top_n=rerank_top_n,
        rerank_keep=rerank_keep,
        hnsw=hnsw,
        ef_search_int=ef_search_int,
        retrieval=retrieval,
        test_set=deps.test_set,
        chunk_set=deps.chunk_set,
        reused=reused,
        sparse_index=deps.sparse_index,
    )
    return metrics, retrieval.latency.p50_ms, retrieval.latency.p95_ms, index_run_id


async def evaluate_retrieval_point(
    *,
    run_id: str,
    point_index: int,
    point: dict[str, Any],
    chunk_set: ChunkSet,
    test_set: TestSet,
    qdrant: QdrantVectorStore,
    embedding: EmbeddingService,
    cache: FsEmbeddingCache,
    sparse_index: SparseBm25Index | None = None,
    persist_index: Callable[..., Any] | None = None,
    rerank_provider: Any | None = None,
    resolve_embedding: ResolveEmbedding | None = None,
    resolve_rerank: ResolveRerank | None = None,
    ensure_embedding: EnsureEmbedding | None = None,
    ensure_rerank: EnsureRerank | None = None,
    index_cache: IndexReuseCache | None = None,
    query_cache: QueryEmbeddingCache | None = None,
    relevance_cache: RelevanceCache | None = None,
) -> tuple[dict[str, Any], float | None, float | None, str | None]:
    """Run one retrieval config; return (metrics, p50, p95, index_run_id)."""
    deps = EvalPointDeps(
        run_id=run_id,
        point_index=point_index,
        point=point,
        chunk_set=chunk_set,
        test_set=test_set,
        qdrant=qdrant,
        embedding=embedding,
        cache=cache,
        sparse_index=sparse_index,
        persist_index=persist_index,
        rerank_provider=rerank_provider,
        resolve_embedding=resolve_embedding,
        resolve_rerank=resolve_rerank,
        ensure_embedding=ensure_embedding,
        ensure_rerank=ensure_rerank,
        index_cache=index_cache,
        query_cache=query_cache,
        relevance_cache=relevance_cache,
    )
    return await _evaluate_with_deps(deps)

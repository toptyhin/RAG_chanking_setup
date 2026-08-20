"""Chunk Lab: compare reference chunker sizes (+ mandatory disclaimer)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from rageval_cache_fs import FsEmbeddingCache, FsSparseIndexCache
from rageval_chunking import chunk_fixed_size
from rageval_domain import ArtifactType, CleanCorpus, TestSet
from rageval_embedding import EmbeddingService
from rageval_metadb_sqlite.experiment_repo import ExperimentRepository
from rageval_orchestrator.eval_point import (
    EnsureEmbedding,
    EnsureRerank,
    IndexReuseCache,
    RelevanceCache,
    evaluate_retrieval_point,
)
from rageval_orchestrator.grid import expand_grid
from rageval_orchestrator.progress import report_progress
from rageval_storage_fs import FileSystemObjectStore
from rageval_retrieval import QueryEmbeddingCache, SparseBm25Index
from rageval_vectordb_qdrant import QdrantVectorStore

LoadModel = Callable[[str, type], Any]

CHUNK_LAB_DISCLAIMER = (
    "Результат относится к алгоритму нарезки RAG-Preparer, а не к chunking'у "
    "целевого проекта (LangChain / свой код / другая схема)."
)

DEFAULT_CHUNK_SWEPT = {"chunk.size": [256, 512]}


@dataclass(slots=True)
class ChunkLabDeps:
    run_id: str
    experiments: ExperimentRepository
    object_store: FileSystemObjectStore
    qdrant: QdrantVectorStore
    embedding: EmbeddingService
    cache_dir: Any
    load_model: LoadModel
    persist_index: Callable[..., Any] | None = None
    persist_chunks: Callable[..., Any] | None = None
    ensure_embedding: EnsureEmbedding | None = None
    ensure_rerank: EnsureRerank | None = None


def _validate_chunk_run(run: Any) -> None:
    if run is None:
        raise LookupError("experiment run not found")
    if run.evaluates != "chunk":
        raise ValueError("only evaluates=chunk is supported")
    if not run.test_set_id:
        raise ValueError("test_set_id is required for chunk lab")
    if run.start_artifact_type != ArtifactType.CLEAN_CORPUS.value:
        raise ValueError("start_artifact must be clean_corpus")


def _default_chunk_swept(run: Any) -> dict[str, Any]:
    swept = run.swept or DEFAULT_CHUNK_SWEPT
    if "chunk.size" not in swept and "chunk.size" not in run.fixed:
        swept = {**DEFAULT_CHUNK_SWEPT, **swept}
    return swept


def _chunk_params(
    point: dict[str, Any],
    run: Any,
    default_overlap: int,
) -> tuple[int, int]:
    size = int(point.get("chunk.size", run.fixed.get("chunk.size", 512)))
    overlap = int(point.get("chunk.overlap", default_overlap))
    if overlap >= size:
        overlap = max(0, size // 8)
    return size, overlap


def _retrieval_point_from(point: dict[str, Any], run: Any) -> dict[str, Any]:
    retrieval_point = {k: v for k, v in point.items() if not k.startswith("chunk.")}
    retrieval_point.setdefault("retrieval.top_k", run.fixed.get("retrieval.top_k", 5))
    retrieval_point.setdefault("retrieval.mode", run.fixed.get("retrieval.mode", "dense"))
    return retrieval_point


async def _resolve_sparse_index(
    *,
    sparse_cache: FsSparseIndexCache,
    sparse_indexes: dict[str, SparseBm25Index],
    chunk_set: Any,
    retrieval_point: dict[str, Any],
) -> SparseBm25Index | None:
    if retrieval_point["retrieval.mode"] not in {"sparse", "hybrid"}:
        return None
    sparse_index = sparse_indexes.get(chunk_set.id)
    if sparse_index is not None:
        return sparse_index
    sparse_index = await asyncio.to_thread(sparse_cache.get_or_build, chunk_set)
    sparse_indexes[chunk_set.id] = sparse_index
    return sparse_index


async def _get_or_persist_chunk_set(
    deps: ChunkLabDeps,
    *,
    corpus: CleanCorpus,
    size: int,
    overlap: int,
    chunk_cache: dict[tuple[int, int], Any],
    persisted_chunks: set[str],
) -> Any:
    chunk_key = (size, overlap)
    chunk_set = chunk_cache.get(chunk_key)
    if chunk_set is None:
        chunk_set = await asyncio.to_thread(
            chunk_fixed_size,
            corpus,
            size=size,
            overlap=overlap,
        )
        chunk_cache[chunk_key] = chunk_set
    if deps.persist_chunks is not None and chunk_set.id not in persisted_chunks:
        await deps.persist_chunks(chunk_set, size=size, overlap=overlap)
        persisted_chunks.add(chunk_set.id)
    return chunk_set


async def _process_chunk_point(
    deps: ChunkLabDeps,
    *,
    run: Any,
    index: int,
    point: dict[str, Any],
    points: list[dict[str, Any]],
    total: int,
    corpus: CleanCorpus,
    test_set: TestSet,
    disclaimer: str,
    default_overlap: int,
    cache: FsEmbeddingCache,
    sparse_cache: FsSparseIndexCache,
    chunk_cache: dict[tuple[int, int], Any],
    persisted_chunks: set[str],
    sparse_indexes: dict[str, SparseBm25Index],
    index_cache: IndexReuseCache,
    query_cache: QueryEmbeddingCache,
    relevance_cache: RelevanceCache,
) -> None:
    size, overlap = _chunk_params(point, run, default_overlap)
    chunk_set = await _get_or_persist_chunk_set(
        deps,
        corpus=corpus,
        size=size,
        overlap=overlap,
        chunk_cache=chunk_cache,
        persisted_chunks=persisted_chunks,
    )
    retrieval_point = _retrieval_point_from(point, run)
    sparse_index = await _resolve_sparse_index(
        sparse_cache=sparse_cache,
        sparse_indexes=sparse_indexes,
        chunk_set=chunk_set,
        retrieval_point=retrieval_point,
    )
    metrics, p50, p95, index_run_id = await evaluate_retrieval_point(
        run_id=deps.run_id,
        point_index=index,
        point=retrieval_point,
        chunk_set=chunk_set,
        test_set=test_set,
        qdrant=deps.qdrant,
        embedding=deps.embedding,
        cache=cache,
        sparse_index=sparse_index,
        persist_index=deps.persist_index,
        ensure_embedding=deps.ensure_embedding,
        ensure_rerank=deps.ensure_rerank,
        index_cache=index_cache,
        query_cache=query_cache,
        relevance_cache=relevance_cache,
    )
    metrics["chunk.size"] = size
    metrics["chunk.overlap"] = overlap
    metrics["chunk_count"] = len(chunk_set.chunks)
    metrics["disclaimer"] = disclaimer
    config_out = {**point, "chunk.size": size, "chunk.overlap": overlap}
    await deps.experiments.add_metrics_row(
        run_id=deps.run_id,
        point_index=index,
        config=config_out,
        metrics=metrics,
        latency_p50_ms=p50,
        latency_p95_ms=p95,
        index_run_id=index_run_id,
        progress_done=index + 1,
        progress_total=total,
        progress_config=points[index + 1] if index + 1 < total else None,
    )


async def _run_chunk_lab(deps: ChunkLabDeps) -> None:
    run = await deps.experiments.get(deps.run_id, with_metrics=False)
    _validate_chunk_run(run)

    disclaimer = run.disclaimer or CHUNK_LAB_DISCLAIMER
    if not run.disclaimer:
        await deps.experiments.set_disclaimer(deps.run_id, disclaimer)
    await deps.experiments.update_status(
        deps.run_id,
        status="running",
        meta={"lab": "chunk", "disclaimer": disclaimer},
        merge_meta=True,
    )

    try:
        corpus: CleanCorpus = deps.load_model(run.start_artifact_id, CleanCorpus)
        test_set: TestSet = deps.load_model(run.test_set_id, TestSet)
        points = expand_grid(run.fixed, _default_chunk_swept(run), max_axes=2)
        cache = FsEmbeddingCache(deps.cache_dir)
        sparse_cache = FsSparseIndexCache(deps.cache_dir)
        chunk_cache: dict[tuple[int, int], Any] = {}
        persisted_chunks: set[str] = set()
        sparse_indexes: dict[str, SparseBm25Index] = {}
        index_cache: IndexReuseCache = {}
        query_cache: QueryEmbeddingCache = {}
        relevance_cache: RelevanceCache = {}
        total = len(points)
        await report_progress(
            deps.experiments,
            deps.run_id,
            done=0,
            total=total,
            current_config=points[0] if points else None,
        )
        default_overlap = int(run.fixed.get("chunk.overlap", 64))

        for index, point in enumerate(points):
            await _process_chunk_point(
                deps,
                run=run,
                index=index,
                point=point,
                points=points,
                total=total,
                corpus=corpus,
                test_set=test_set,
                disclaimer=disclaimer,
                default_overlap=default_overlap,
                cache=cache,
                sparse_cache=sparse_cache,
                chunk_cache=chunk_cache,
                persisted_chunks=persisted_chunks,
                sparse_indexes=sparse_indexes,
                index_cache=index_cache,
                query_cache=query_cache,
                relevance_cache=relevance_cache,
            )

        await deps.experiments.update_status(deps.run_id, status="completed")
    except Exception as exc:  # noqa: BLE001
        await deps.experiments.update_status(deps.run_id, status="failed", error=str(exc))


async def run_chunk_lab(
    *,
    run_id: str,
    experiments: ExperimentRepository,
    object_store: FileSystemObjectStore,
    qdrant: QdrantVectorStore,
    embedding: EmbeddingService,
    cache_dir,
    load_model: LoadModel,
    persist_index: Callable[..., Any] | None = None,
    persist_chunks: Callable[..., Any] | None = None,
    ensure_embedding: EnsureEmbedding | None = None,
    ensure_rerank: EnsureRerank | None = None,
) -> None:
    await _run_chunk_lab(
        ChunkLabDeps(
            run_id=run_id,
            experiments=experiments,
            object_store=object_store,
            qdrant=qdrant,
            embedding=embedding,
            cache_dir=cache_dir,
            load_model=load_model,
            persist_index=persist_index,
            persist_chunks=persist_chunks,
            ensure_embedding=ensure_embedding,
            ensure_rerank=ensure_rerank,
        )
    )

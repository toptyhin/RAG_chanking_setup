"""Retrieval Lab orchestrator (single config or small grid)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from rageval_cache_fs import FsEmbeddingCache, FsSparseIndexCache
from rageval_domain import ArtifactType, ChunkSet, TestSet
from rageval_embedding import EmbeddingService
from rageval_metadb_sqlite.experiment_repo import ExperimentRepository
from rageval_metadb_sqlite.repositories import ArtifactRepository
from rageval_orchestrator.eval_point import (
    EnsureEmbedding,
    EnsureRerank,
    IndexReuseCache,
    RelevanceCache,
    ResolveEmbedding,
    ResolveRerank,
    evaluate_retrieval_point,
    index_group_key,
)
from rageval_orchestrator.grid import expand_grid
from rageval_orchestrator.progress import report_progress
from rageval_retrieval import QueryEmbeddingCache, SparseBm25Index
from rageval_storage_fs import FileSystemObjectStore
from rageval_vectordb_qdrant import QdrantVectorStore

LoadModel = Callable[[str, type], Any]


@dataclass(slots=True)
class RetrievalLabDeps:
    run_id: str
    experiments: ExperimentRepository
    artifacts: ArtifactRepository
    object_store: FileSystemObjectStore
    qdrant: QdrantVectorStore
    embedding: EmbeddingService
    cache_dir: Any
    load_model: LoadModel
    persist_index: Callable[..., Any] | None = None
    rerank_provider: Any | None = None
    resolve_embedding: ResolveEmbedding | None = None
    resolve_rerank: ResolveRerank | None = None
    ensure_embedding: EnsureEmbedding | None = None
    ensure_rerank: EnsureRerank | None = None


def _needs_sparse(points: list[dict[str, Any]]) -> bool:
    return any(
        str(p.get("retrieval.mode", "dense")).lower() in {"sparse", "hybrid"}
        for p in points
    )


def _validate_retrieval_run(run: Any) -> None:
    if run is None:
        raise LookupError("experiment run not found")
    if run.evaluates != "retrieval":
        raise ValueError("only evaluates=retrieval is supported")
    if not run.test_set_id:
        raise ValueError("test_set_id is required for retrieval lab")
    if run.start_artifact_type != ArtifactType.CHUNK_SET.value:
        raise ValueError("start_artifact must be chunk_set")


def _group_points(
    points: list[dict[str, Any]],
    *,
    chunk_set: ChunkSet,
    embedding: EmbeddingService,
) -> list[tuple[int, dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[tuple[int, dict[str, Any]]]] = {}
    for point_index, point in enumerate(points):
        key = index_group_key(
            point,
            chunk_set_id=chunk_set.id,
            default_model=embedding.provider.model_name,
            default_dimension=embedding.dimension,
        )
        grouped.setdefault(key, []).append((point_index, point))
    return [item for group in grouped.values() for item in group]


async def _evaluate_point_or_fail(
    deps: RetrievalLabDeps,
    *,
    point_index: int,
    point: dict[str, Any],
    chunk_set: ChunkSet,
    test_set: TestSet,
    cache: FsEmbeddingCache,
    sparse_index: SparseBm25Index | None,
    index_cache: IndexReuseCache,
    query_cache: QueryEmbeddingCache,
    relevance_cache: RelevanceCache,
) -> tuple[dict[str, Any], float | None, float | None, str | None, bool]:
    try:
        metrics, p50, p95, index_run_id = await evaluate_retrieval_point(
            run_id=deps.run_id,
            point_index=point_index,
            point=point,
            chunk_set=chunk_set,
            test_set=test_set,
            qdrant=deps.qdrant,
            embedding=deps.embedding,
            cache=cache,
            sparse_index=sparse_index,
            persist_index=deps.persist_index,
            rerank_provider=deps.rerank_provider,
            resolve_embedding=deps.resolve_embedding,
            resolve_rerank=deps.resolve_rerank,
            ensure_embedding=deps.ensure_embedding,
            ensure_rerank=deps.ensure_rerank,
            index_cache=index_cache,
            query_cache=query_cache,
            relevance_cache=relevance_cache,
        )
        return metrics, p50, p95, index_run_id, False
    except Exception as point_exc:  # noqa: BLE001
        return (
            {"status": "failed", "error": str(point_exc)},
            None,
            None,
            None,
            True,
        )


async def _run_retrieval_lab(deps: RetrievalLabDeps) -> None:
    """Execute retrieval grid for an existing pending experiment run."""
    run = await deps.experiments.get(deps.run_id, with_metrics=False)
    _validate_retrieval_run(run)
    await deps.experiments.update_status(deps.run_id, status="running")

    try:
        chunk_set: ChunkSet = deps.load_model(run.start_artifact_id, ChunkSet)
        test_set: TestSet = deps.load_model(run.test_set_id, TestSet)
        points = expand_grid(run.fixed, run.swept, max_axes=2)
        cache = FsEmbeddingCache(deps.cache_dir)
        sparse_index: SparseBm25Index | None = None
        if _needs_sparse(points):
            sparse_cache = FsSparseIndexCache(deps.cache_dir)
            sparse_index = await asyncio.to_thread(
                sparse_cache.get_or_build,
                chunk_set,
            )
        ordered_points = _group_points(points, chunk_set=chunk_set, embedding=deps.embedding)
        index_cache: IndexReuseCache = {}
        query_cache: QueryEmbeddingCache = {}
        relevance_cache: RelevanceCache = {}
        total = len(points)
        await report_progress(
            deps.experiments,
            deps.run_id,
            done=0,
            total=total,
            current_config=ordered_points[0][1] if ordered_points else None,
        )

        failed_points = 0
        for done, (point_index, point) in enumerate(ordered_points):
            metrics, p50, p95, index_run_id, failed = await _evaluate_point_or_fail(
                deps,
                point_index=point_index,
                point=point,
                chunk_set=chunk_set,
                test_set=test_set,
                cache=cache,
                sparse_index=sparse_index,
                index_cache=index_cache,
                query_cache=query_cache,
                relevance_cache=relevance_cache,
            )
            if failed:
                failed_points += 1
            next_config = ordered_points[done + 1][1] if done + 1 < total else None
            await deps.experiments.add_metrics_row(
                run_id=deps.run_id,
                point_index=point_index,
                config=point,
                metrics=metrics,
                latency_p50_ms=p50,
                latency_p95_ms=p95,
                index_run_id=index_run_id,
                progress_done=done + 1,
                progress_total=total,
                progress_config=next_config,
            )

        meta_patch: dict[str, Any] = {}
        if failed_points:
            meta_patch["failed_points"] = failed_points
        await deps.experiments.update_status(
            deps.run_id,
            status="completed",
            meta=meta_patch or None,
            merge_meta=bool(meta_patch),
        )
    except Exception as exc:  # noqa: BLE001
        await deps.experiments.update_status(deps.run_id, status="failed", error=str(exc))


async def run_retrieval_lab(
    *,
    run_id: str,
    experiments: ExperimentRepository,
    artifacts: ArtifactRepository,
    object_store: FileSystemObjectStore,
    qdrant: QdrantVectorStore,
    embedding: EmbeddingService,
    cache_dir,
    load_model: LoadModel,
    persist_index: Callable[..., Any] | None = None,
    rerank_provider: Any | None = None,
    resolve_embedding: ResolveEmbedding | None = None,
    resolve_rerank: ResolveRerank | None = None,
    ensure_embedding: EnsureEmbedding | None = None,
    ensure_rerank: EnsureRerank | None = None,
) -> None:
    await _run_retrieval_lab(
        RetrievalLabDeps(
            run_id=run_id,
            experiments=experiments,
            artifacts=artifacts,
            object_store=object_store,
            qdrant=qdrant,
            embedding=embedding,
            cache_dir=cache_dir,
            load_model=load_model,
            persist_index=persist_index,
            rerank_provider=rerank_provider,
            resolve_embedding=resolve_embedding,
            resolve_rerank=resolve_rerank,
            ensure_embedding=ensure_embedding,
            ensure_rerank=ensure_rerank,
        )
    )

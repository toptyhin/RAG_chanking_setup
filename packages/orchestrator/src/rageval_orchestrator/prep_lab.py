"""Prep Lab: compare prep pipelines on downstream Recall."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from rageval_cache_fs import FsEmbeddingCache, FsSparseIndexCache
from rageval_chunking import chunk_fixed_size
from rageval_domain import ArtifactType, RawBundle, TestSet
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
from rageval_prep import PrepPipelineId, run_prep
from rageval_retrieval import QueryEmbeddingCache, SparseBm25Index
from rageval_storage_fs import FileSystemObjectStore
from rageval_vectordb_qdrant import QdrantVectorStore

LoadModel = Callable[[str, type], Any]
LoadFile = Callable[[str], bytes]

PREP_LAB_DISCLAIMER = (
    "Prep Lab compares extraction/cleanup pipelines on a fixed chunk+embed+retrieve "
    "baseline. Results are relative to this lab setup, not a full corpus hygiene suite."
)

DEFAULT_PREP_SWEPT = {
    "prep.pipeline": [PrepPipelineId.PLAINTEXT.value, PrepPipelineId.PDF_CLEAN.value]
}


@dataclass(slots=True)
class PrepLabDeps:
    run_id: str
    experiments: ExperimentRepository
    object_store: FileSystemObjectStore
    qdrant: QdrantVectorStore
    embedding: EmbeddingService
    cache_dir: Any
    load_model: LoadModel
    load_file: LoadFile
    persist_index: Callable[..., Any] | None = None
    persist_clean: Callable[..., Any] | None = None
    ensure_embedding: EnsureEmbedding | None = None
    ensure_rerank: EnsureRerank | None = None
    prepared_corpora: dict[str, tuple[Any, dict[str, Any]]] | None = None


def _validate_prep_run(run: Any) -> None:
    if run is None:
        raise LookupError("experiment run not found")
    if run.evaluates != "prep":
        raise ValueError("only evaluates=prep is supported")
    if not run.test_set_id:
        raise ValueError("test_set_id is required for prep lab")
    if run.start_artifact_type != ArtifactType.RAW_BUNDLE.value:
        raise ValueError("start_artifact must be raw_bundle")


def _default_prep_swept(run: Any) -> dict[str, Any]:
    swept = run.swept or DEFAULT_PREP_SWEPT
    if "prep.pipeline" not in swept and "prep.pipeline" not in run.fixed:
        swept = {**DEFAULT_PREP_SWEPT, **swept}
    return swept


def _retrieval_point_from(
    point: dict[str, Any],
    run: Any,
) -> dict[str, Any]:
    retrieval_point = {
        k: v
        for k, v in point.items()
        if not k.startswith("prep.") and not k.startswith("chunk.")
    }
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


async def _prepare_corpus(
    deps: PrepLabDeps,
    *,
    bundle: RawBundle,
    pipeline: str,
    corpus_cache: dict[str, tuple[Any, dict[str, Any]]],
) -> tuple[Any, dict[str, Any]]:
    prepared = corpus_cache.get(pipeline)
    if prepared is not None:
        return prepared
    corpus, prep_metrics_obj = await asyncio.to_thread(
        run_prep,
        bundle,
        load_file=deps.load_file,
        pipeline_id=pipeline,
    )
    prep_metrics = prep_metrics_obj.as_dict()
    corpus_cache[pipeline] = (corpus, prep_metrics)
    if deps.persist_clean is not None:
        await deps.persist_clean(corpus, prep_metrics)
    return corpus, prep_metrics


async def _get_chunk_set(
    corpus: Any,
    *,
    chunk_size: int,
    chunk_overlap: int,
    chunk_cache: dict[tuple[str, int, int], Any],
) -> Any:
    chunk_key = (corpus.id, chunk_size, chunk_overlap)
    chunk_set = chunk_cache.get(chunk_key)
    if chunk_set is not None:
        return chunk_set
    chunk_set = await asyncio.to_thread(
        chunk_fixed_size,
        corpus,
        size=chunk_size,
        overlap=chunk_overlap,
    )
    chunk_cache[chunk_key] = chunk_set
    return chunk_set


async def _process_prep_point(
    deps: PrepLabDeps,
    *,
    run: Any,
    index: int,
    point: dict[str, Any],
    points: list[dict[str, Any]],
    total: int,
    bundle: RawBundle,
    test_set: TestSet,
    chunk_size: int,
    chunk_overlap: int,
    cache: FsEmbeddingCache,
    sparse_cache: FsSparseIndexCache,
    corpus_cache: dict[str, tuple[Any, dict[str, Any]]],
    chunk_cache: dict[tuple[str, int, int], Any],
    sparse_indexes: dict[str, SparseBm25Index],
    index_cache: IndexReuseCache,
    query_cache: QueryEmbeddingCache,
    relevance_cache: RelevanceCache,
) -> None:
    pipeline = str(point.get("prep.pipeline", PrepPipelineId.DEFAULT.value))
    corpus, prep_metrics = await _prepare_corpus(
        deps, bundle=bundle, pipeline=pipeline, corpus_cache=corpus_cache
    )
    chunk_set = await _get_chunk_set(
        corpus, chunk_size=chunk_size, chunk_overlap=chunk_overlap, chunk_cache=chunk_cache
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
    metrics["prep_pipeline"] = pipeline
    metrics["prep"] = prep_metrics
    metrics["chunk_count"] = len(chunk_set.chunks)
    config_out = {
        **point,
        "prep.pipeline": pipeline,
        "chunk.size": chunk_size,
        "chunk.overlap": chunk_overlap,
    }
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


async def _run_prep_lab(deps: PrepLabDeps) -> None:
    run = await deps.experiments.get(deps.run_id, with_metrics=False)
    _validate_prep_run(run)

    disclaimer = run.disclaimer or PREP_LAB_DISCLAIMER
    if not run.disclaimer:
        await deps.experiments.set_disclaimer(deps.run_id, disclaimer)
    await deps.experiments.update_status(
        deps.run_id,
        status="running",
        meta={"lab": "prep", "disclaimer": disclaimer},
        merge_meta=True,
    )

    try:
        bundle: RawBundle = deps.load_model(run.start_artifact_id, RawBundle)
        test_set: TestSet = deps.load_model(run.test_set_id, TestSet)
        points = expand_grid(run.fixed, _default_prep_swept(run), max_axes=2)
        cache = FsEmbeddingCache(deps.cache_dir)
        sparse_cache = FsSparseIndexCache(deps.cache_dir)
        corpus_cache = dict(deps.prepared_corpora or {})
        chunk_cache: dict[tuple[str, int, int], Any] = {}
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
        chunk_size = int(run.fixed.get("chunk.size", 512))
        chunk_overlap = int(run.fixed.get("chunk.overlap", 64))

        for index, point in enumerate(points):
            await _process_prep_point(
                deps,
                run=run,
                index=index,
                point=point,
                points=points,
                total=total,
                bundle=bundle,
                test_set=test_set,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                cache=cache,
                sparse_cache=sparse_cache,
                corpus_cache=corpus_cache,
                chunk_cache=chunk_cache,
                sparse_indexes=sparse_indexes,
                index_cache=index_cache,
                query_cache=query_cache,
                relevance_cache=relevance_cache,
            )

        await deps.experiments.update_status(deps.run_id, status="completed")
    except Exception as exc:  # noqa: BLE001
        await deps.experiments.update_status(deps.run_id, status="failed", error=str(exc))


async def run_prep_lab(
    *,
    run_id: str,
    experiments: ExperimentRepository,
    object_store: FileSystemObjectStore,
    qdrant: QdrantVectorStore,
    embedding: EmbeddingService,
    cache_dir,
    load_model: LoadModel,
    load_file: LoadFile,
    persist_index: Callable[..., Any] | None = None,
    persist_clean: Callable[..., Any] | None = None,
    ensure_embedding: EnsureEmbedding | None = None,
    ensure_rerank: EnsureRerank | None = None,
    prepared_corpora: dict[str, tuple[Any, dict[str, Any]]] | None = None,
) -> None:
    await _run_prep_lab(
        PrepLabDeps(
            run_id=run_id,
            experiments=experiments,
            object_store=object_store,
            qdrant=qdrant,
            embedding=embedding,
            cache_dir=cache_dir,
            load_model=load_model,
            load_file=load_file,
            persist_index=persist_index,
            persist_clean=persist_clean,
            ensure_embedding=ensure_embedding,
            ensure_rerank=ensure_rerank,
            prepared_corpora=prepared_corpora,
        )
    )

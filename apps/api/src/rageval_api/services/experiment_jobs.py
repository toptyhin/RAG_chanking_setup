"""Background experiment execution wired to LocalTaskRunner."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from rageval_api.services.artifact_io import load_artifact_model, persist_artifact_model
from rageval_domain import (
    ArtifactType,
    ChunkSet,
    CleanCorpus,
    IndexRun,
    RawBundle,
    TestSet,
)
from rageval_embedding import EmbeddingService
from rageval_metadb_sqlite.experiment_repo import ExperimentRepository
from rageval_metadb_sqlite.repositories import ArtifactRepository
from rageval_orchestrator import (
    CHUNK_LAB_DISCLAIMER,
    finalize_run,
    run_chunk_lab,
    run_prep_lab,
    run_retrieval_lab,
)
from rageval_storage_fs import FileSystemObjectStore
from rageval_vectordb_qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExperimentJobDeps:
    run_id: str
    session_factory: async_sessionmaker[AsyncSession]
    object_store: FileSystemObjectStore
    qdrant: QdrantVectorStore
    embedding: EmbeddingService
    cache_dir: Any
    model_registry: Any | None = None


@dataclass(slots=True)
class _JobContext:
    run_id: str
    run: Any
    experiments: ExperimentRepository
    artifacts: ArtifactRepository
    object_store: FileSystemObjectStore
    qdrant: QdrantVectorStore
    embedding: EmbeddingService
    cache_dir: Any
    models: dict[str, Any]
    ensure_embedding: Any | None
    ensure_rerank: Any | None

    async def ensure_model(self, artifact_id: str, model_type: type, expected: str) -> Any:
        if artifact_id in self.models:
            return self.models[artifact_id]
        _, model = await load_artifact_model(
            self.artifacts,
            self.object_store,
            artifact_id,
            model_type,
            expected_type=expected,
        )
        self.models[artifact_id] = model
        return model

    def load_model_sync(self, artifact_id: str, model_type: type) -> Any:
        model = self.models.get(artifact_id)
        if model is None or not isinstance(model, model_type):
            raise LookupError(f"model not preloaded: {artifact_id}")
        return model

    async def persist_index(self, index_run: IndexRun, chunk_set_id: str) -> str:
        record = await persist_artifact_model(
            self.artifacts,
            self.object_store,
            model=index_run,
            artifact_id=index_run.id,
            project_id=self.run.project_id,
            artifact_type=ArtifactType.INDEX_RUN.value,
            parent_ids=[chunk_set_id, self.run_id],
            meta={
                "collection_name": index_run.collection_name,
                "experiment_run_id": self.run_id,
            },
        )
        return record.id


async def _run_retrieval_job(ctx: _JobContext) -> None:
    await ctx.ensure_model(ctx.run.start_artifact_id, ChunkSet, "chunk_set")
    assert ctx.run.test_set_id
    await ctx.ensure_model(ctx.run.test_set_id, TestSet, "test_set")
    await run_retrieval_lab(
        run_id=ctx.run_id,
        experiments=ctx.experiments,
        artifacts=ctx.artifacts,
        object_store=ctx.object_store,
        qdrant=ctx.qdrant,
        embedding=ctx.embedding,
        cache_dir=ctx.cache_dir,
        load_model=ctx.load_model_sync,
        persist_index=ctx.persist_index,
        ensure_embedding=ctx.ensure_embedding,
        ensure_rerank=ctx.ensure_rerank,
    )


async def _load_default_prep_corpus(ctx: _JobContext) -> dict[str, tuple[Any, dict[str, Any]]]:
    prepared_corpora: dict[str, tuple[Any, dict[str, Any]]] = {}
    for child in await ctx.artifacts.list_dependents(
        ctx.run.start_artifact_id,
        project_id=ctx.run.project_id,
    ):
        if (
            child.type == ArtifactType.CLEAN_CORPUS.value
            and child.meta.get("prep_pipeline_id") == "default"
        ):
            _, prepared = await load_artifact_model(
                ctx.artifacts,
                ctx.object_store,
                child.id,
                CleanCorpus,
                expected_type=ArtifactType.CLEAN_CORPUS.value,
            )
            prepared_corpora["default"] = (
                prepared,
                dict(child.meta.get("prep_metrics") or {}),
            )
            break
    return prepared_corpora


async def _run_prep_job(ctx: _JobContext) -> None:
    await ctx.ensure_model(ctx.run.start_artifact_id, RawBundle, "raw_bundle")
    assert ctx.run.test_set_id
    await ctx.ensure_model(ctx.run.test_set_id, TestSet, "test_set")
    prepared_corpora = await _load_default_prep_corpus(ctx)

    async def persist_clean(corpus: CleanCorpus, prep_metrics: dict) -> None:
        await persist_artifact_model(
            ctx.artifacts,
            ctx.object_store,
            model=corpus,
            artifact_id=corpus.id,
            project_id=ctx.run.project_id,
            artifact_type=ArtifactType.CLEAN_CORPUS.value,
            parent_ids=[ctx.run.start_artifact_id, ctx.run_id],
            meta={
                "prep_pipeline_id": corpus.prep_pipeline_id,
                "document_count": len(corpus.documents),
                "prep_metrics": prep_metrics,
                "experiment_run_id": ctx.run_id,
            },
        )

    await run_prep_lab(
        run_id=ctx.run_id,
        experiments=ctx.experiments,
        object_store=ctx.object_store,
        qdrant=ctx.qdrant,
        embedding=ctx.embedding,
        cache_dir=ctx.cache_dir,
        load_model=ctx.load_model_sync,
        load_file=ctx.object_store.get,
        persist_index=ctx.persist_index,
        persist_clean=persist_clean,
        ensure_embedding=ctx.ensure_embedding,
        ensure_rerank=ctx.ensure_rerank,
        prepared_corpora=prepared_corpora,
    )


async def _run_chunk_job(ctx: _JobContext) -> None:
    await ctx.ensure_model(ctx.run.start_artifact_id, CleanCorpus, "clean_corpus")
    assert ctx.run.test_set_id
    await ctx.ensure_model(ctx.run.test_set_id, TestSet, "test_set")
    if not ctx.run.disclaimer:
        await ctx.experiments.set_disclaimer(ctx.run_id, CHUNK_LAB_DISCLAIMER)

    async def persist_chunks(chunk_set: ChunkSet, *, size: int, overlap: int) -> None:
        from rageval_api.services.chunk_length_stats import length_chars_from_chunks

        length_chars = length_chars_from_chunks(chunk_set.chunks)
        await persist_artifact_model(
            ctx.artifacts,
            ctx.object_store,
            model=chunk_set,
            artifact_id=chunk_set.id,
            project_id=ctx.run.project_id,
            artifact_type=ArtifactType.CHUNK_SET.value,
            parent_ids=[ctx.run.start_artifact_id, ctx.run_id],
            meta={
                "chunk_pipeline_id": chunk_set.chunk_pipeline_id,
                "chunk_count": len(chunk_set.chunks),
                **({"length_chars": length_chars} if length_chars else {}),
                "size": size,
                "overlap": overlap,
                "experiment_run_id": ctx.run_id,
            },
        )

    await run_chunk_lab(
        run_id=ctx.run_id,
        experiments=ctx.experiments,
        object_store=ctx.object_store,
        qdrant=ctx.qdrant,
        embedding=ctx.embedding,
        cache_dir=ctx.cache_dir,
        load_model=ctx.load_model_sync,
        persist_index=ctx.persist_index,
        persist_chunks=persist_chunks,
        ensure_embedding=ctx.ensure_embedding,
        ensure_rerank=ctx.ensure_rerank,
    )


async def _dispatch_lab(ctx: _JobContext) -> bool:
    evaluates = ctx.run.evaluates
    if evaluates == "retrieval":
        await _run_retrieval_job(ctx)
        return True
    if evaluates == "prep":
        await _run_prep_job(ctx)
        return True
    if evaluates == "chunk":
        await _run_chunk_job(ctx)
        return True
    await ctx.experiments.update_status(
        ctx.run_id,
        status="failed",
        error=f"unsupported evaluates={evaluates!r}",
    )
    return False


async def _persist_job_failure(
    deps: ExperimentJobDeps,
    exc: Exception,
) -> None:
    logger.exception("experiment job failed: %s", deps.run_id)
    try:
        async with deps.session_factory() as err_session:
            err_repo = ExperimentRepository(err_session)
            current = await err_repo.get(deps.run_id, with_metrics=False)
            if current is not None and current.status not in {"failed", "completed"}:
                await err_repo.update_status(deps.run_id, status="failed", error=str(exc))
            await err_session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("failed to persist error status for %s", deps.run_id)


async def _execute_experiment_job(deps: ExperimentJobDeps) -> None:
    async with deps.session_factory() as session:
        experiments = ExperimentRepository(session)
        artifacts = ArtifactRepository(session)
        try:
            run = await experiments.get(deps.run_id, with_metrics=False)
            if run is None:
                logger.error("experiment missing for job: %s", deps.run_id)
                return

            ensure_embedding = None
            ensure_rerank = None
            if deps.model_registry is not None:
                ensure_embedding = deps.model_registry.ensure_embedding
                ensure_rerank = deps.model_registry.ensure_rerank

            ctx = _JobContext(
                run_id=deps.run_id,
                run=run,
                experiments=experiments,
                artifacts=artifacts,
                object_store=deps.object_store,
                qdrant=deps.qdrant,
                embedding=deps.embedding,
                cache_dir=deps.cache_dir,
                models={},
                ensure_embedding=ensure_embedding,
                ensure_rerank=ensure_rerank,
            )
            ran = await _dispatch_lab(ctx)
            if not ran:
                await session.commit()
                return

            completed = await experiments.get(deps.run_id, with_metrics=False)
            if completed is not None and completed.status == "completed":
                await finalize_run(
                    run_id=deps.run_id,
                    experiments=experiments,
                    object_store=deps.object_store,
                )
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            await _persist_job_failure(deps, exc)


async def execute_experiment_job(
    *,
    run_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    object_store: FileSystemObjectStore,
    qdrant: QdrantVectorStore,
    embedding: EmbeddingService,
    cache_dir: Any,
    model_registry: Any | None = None,
) -> None:
    await _execute_experiment_job(
        ExperimentJobDeps(
            run_id=run_id,
            session_factory=session_factory,
            object_store=object_store,
            qdrant=qdrant,
            embedding=embedding,
            cache_dir=cache_dir,
            model_registry=model_registry,
        )
    )

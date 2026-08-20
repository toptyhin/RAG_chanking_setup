"""Shared prep execution for API routes."""

from __future__ import annotations

import asyncio

from rageval_api.services.artifact_io import persist_artifact_model
from rageval_api.services.artifact_naming import (
    naming_meta,
    source_name_from_filenames,
    source_name_from_record,
)
from rageval_domain import ArtifactType, RawBundle
from rageval_metadb_sqlite.repositories import ArtifactRecord, ArtifactRepository
from rageval_prep import PrepPipelineId, PrepMetrics, run_prep
from rageval_storage_fs import FileSystemObjectStore


async def prepare_clean_corpus(
    *,
    project_id: str,
    raw_record: ArtifactRecord,
    bundle: RawBundle,
    pipeline: PrepPipelineId | str = PrepPipelineId.DEFAULT,
    artifacts: ArtifactRepository,
    store: FileSystemObjectStore,
) -> tuple[ArtifactRecord, PrepMetrics]:
    """Run prep on a raw bundle and persist the resulting clean_corpus."""

    def load_file(key: str) -> bytes:
        return store.get(key)

    corpus, metrics = await asyncio.to_thread(
        run_prep,
        bundle,
        load_file=load_file,
        pipeline_id=pipeline,
    )
    source = source_name_from_record(raw_record) or source_name_from_filenames(
        [f.original_name for f in bundle.files]
    )
    record = await persist_artifact_model(
        artifacts,
        store,
        model=corpus,
        artifact_id=corpus.id,
        project_id=project_id,
        artifact_type=ArtifactType.CLEAN_CORPUS.value,
        parent_ids=[bundle.id],
        meta={
            "prep_pipeline_id": corpus.prep_pipeline_id,
            "document_count": len(corpus.documents),
            "prep_metrics": metrics.as_dict(),
            **naming_meta(ArtifactType.CLEAN_CORPUS.value, source),
        },
    )
    return record, metrics

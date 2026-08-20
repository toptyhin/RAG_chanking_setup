from __future__ import annotations

import asyncio
import hashlib
from pathlib import PurePosixPath

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from rageval_api.deps import (
    ArtifactRepoDep,
    ExperimentRepoDep,
    ObjectStoreDep,
    ProjectRepoDep,
)
from rageval_api.schemas import (
    ArtifactDeleteResponse,
    ArtifactImportRequest,
    ArtifactImportResponse,
    ArtifactOut,
    RawBundleUploadResponse,
)
from rageval_api.services.artifact_delete import (
    ArtifactDeleteError,
    delete_artifact,
)
from rageval_api.services.artifact_import import (
    ArtifactImportError,
    import_artifacts_from_project,
)
from rageval_api.services.artifact_meta import enrich_meta
from rageval_api.services.artifact_naming import (
    display_name,
    source_name_from_filenames,
)
from rageval_api.services.prep_run import prepare_clean_corpus
from rageval_domain import ArtifactType, RawBundle, RawFileRef, new_id
from rageval_metadb_sqlite.repositories import ArtifactRecord, ArtifactRepository
from rageval_prep import PrepPipelineId
from rageval_storage_fs import FileSystemObjectStore

router = APIRouter(tags=["artifacts"])


async def _to_out(
    record: ArtifactRecord,
    store: FileSystemObjectStore | None = None,
    artifacts: ArtifactRepository | None = None,
) -> ArtifactOut:
    meta = record.meta
    if store is not None:
        meta = await enrich_meta(record, store, artifacts)
    return ArtifactOut(
        id=record.id,
        project_id=record.project_id,
        type=record.type,
        parent_ids=record.parent_ids,
        content_hash=record.content_hash,
        object_key=record.object_key,
        meta=meta,
        created_at=record.created_at,
    )


@router.get("/projects/{project_id}/artifacts", response_model=list[ArtifactOut])
async def list_artifacts(
    project_id: str,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
    type: str | None = None,
) -> list[ArtifactOut]:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    rows = await artifacts.list_for_project(project_id, artifact_type=type)
    return [await _to_out(r, store, artifacts) for r in rows]


@router.post(
    "/projects/{project_id}/artifacts/import",
    response_model=ArtifactImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_artifacts(
    project_id: str,
    body: ArtifactImportRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> ArtifactImportResponse:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    if await projects.get(body.source_project_id) is None:
        raise HTTPException(status_code=404, detail="source project not found")

    try:
        created, id_map = await import_artifacts_from_project(
            target_project_id=project_id,
            source_project_id=body.source_project_id,
            artifact_ids=body.artifact_ids,
            include_parents=body.include_parents,
            artifacts=artifacts,
            store=store,
        )
    except ArtifactImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return ArtifactImportResponse(
        artifacts=[await _to_out(r, store, artifacts) for r in created],
        id_map=id_map,
    )


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(
    artifact_id: str,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> ArtifactOut:
    row = await artifacts.get(artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return await _to_out(row, store, artifacts)


@router.delete(
    "/artifacts/{artifact_id}",
    response_model=ArtifactDeleteResponse,
)
async def delete_artifact_endpoint(
    artifact_id: str,
    request: Request,
    artifacts: ArtifactRepoDep,
    experiments: ExperimentRepoDep,
    store: ObjectStoreDep,
    cascade: bool = False,
) -> ArtifactDeleteResponse:
    try:
        deleted = await delete_artifact(
            artifact_id=artifact_id,
            cascade=cascade,
            artifacts=artifacts,
            experiments=experiments,
            store=store,
            vector_store=getattr(request.app.state, "qdrant", None),
        )
    except ArtifactDeleteError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return ArtifactDeleteResponse(deleted=deleted)


@router.post(
    "/projects/{project_id}/raw-bundles",
    response_model=RawBundleUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_raw_bundle(
    project_id: str,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
    files: list[UploadFile] = File(...),
) -> RawBundleUploadResponse:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    if not files:
        raise HTTPException(status_code=400, detail="at least one file required")

    raw_id = new_id("raw")
    file_refs: list[RawFileRef] = []
    digest = hashlib.sha256()

    for upload in files:
        original = PurePosixPath(upload.filename or "unnamed").name
        data = await upload.read()
        digest.update(data)
        digest.update(original.encode("utf-8"))
        key = f"{raw_id}/files/{original}"
        sha = await asyncio.to_thread(store.put, key, data)
        file_refs.append(
            RawFileRef(
                path=key,
                original_name=original,
                content_type=upload.content_type,
                size_bytes=len(data),
                sha256=sha,
            )
        )

    bundle = RawBundle(id=raw_id, project_id=project_id, files=file_refs)
    manifest_key = f"{raw_id}/manifest.json"
    manifest_bytes = bundle.model_dump_json().encode("utf-8")
    await asyncio.to_thread(store.put, manifest_key, manifest_bytes)

    source = source_name_from_filenames([f.original_name for f in file_refs])
    record = await artifacts.create(
        artifact_id=raw_id,
        project_id=project_id,
        artifact_type=ArtifactType.RAW_BUNDLE.value,
        parent_ids=[],
        content_hash=digest.hexdigest(),
        object_key=manifest_key,
        meta={
            "file_count": len(file_refs),
            "source_name": source,
            "display_name": display_name(ArtifactType.RAW_BUNDLE.value, source),
        },
    )

    clean_record, prep_metrics = await prepare_clean_corpus(
        project_id=project_id,
        raw_record=record,
        bundle=bundle,
        pipeline=PrepPipelineId.DEFAULT,
        artifacts=artifacts,
        store=store,
    )
    return RawBundleUploadResponse(
        artifact=await _to_out(record, store, artifacts),
        files_stored=len(file_refs),
        clean_corpus=await _to_out(clean_record, store, artifacts),
        document_count=int(clean_record.meta.get("document_count") or 0),
        prep_metrics=prep_metrics.as_dict(),
    )

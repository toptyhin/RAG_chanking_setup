"""Load/save domain artifacts via ObjectStore + ArtifactRegistry."""

from __future__ import annotations

import asyncio
import json
from typing import TypeVar

from pydantic import BaseModel

from rageval_metadb_sqlite.repositories import ArtifactRecord, ArtifactRepository
from rageval_storage_fs import FileSystemObjectStore

T = TypeVar("T", bound=BaseModel)


async def load_artifact_model(
    artifacts: ArtifactRepository,
    store: FileSystemObjectStore,
    artifact_id: str,
    model_type: type[T],
    *,
    expected_type: str | None = None,
) -> tuple[ArtifactRecord, T]:
    record = await artifacts.get(artifact_id)
    if record is None:
        raise LookupError("artifact not found")
    if expected_type is not None and record.type != expected_type:
        raise ValueError(f"expected artifact type {expected_type}, got {record.type}")
    if not record.object_key:
        raise ValueError("artifact has no object_key")
    data = await asyncio.to_thread(store.get, record.object_key)
    payload = json.loads(data.decode("utf-8"))
    return record, model_type.model_validate(payload)


async def persist_artifact_model(
    artifacts: ArtifactRepository,
    store: FileSystemObjectStore,
    *,
    model: BaseModel,
    artifact_id: str,
    project_id: str,
    artifact_type: str,
    parent_ids: list[str],
    meta: dict | None = None,
) -> ArtifactRecord:
    existing = await artifacts.get(artifact_id)
    if existing is not None:
        if existing.project_id != project_id or existing.type != artifact_type:
            raise ValueError(f"artifact id collision: {artifact_id}")
        return existing
    object_key = f"{artifact_id}/manifest.json"
    data = model.model_dump_json().encode("utf-8")
    content_hash = await asyncio.to_thread(store.put, object_key, data)
    return await artifacts.create(
        artifact_id=artifact_id,
        project_id=project_id,
        artifact_type=artifact_type,
        parent_ids=parent_ids,
        content_hash=content_hash,
        object_key=object_key,
        meta=meta or {},
    )


async def update_artifact_model(
    artifacts: ArtifactRepository,
    store: FileSystemObjectStore,
    *,
    model: BaseModel,
    artifact_id: str,
    meta: dict | None = None,
) -> ArtifactRecord:
    """Overwrite an existing artifact blob + meta (immutable content hash updates)."""
    object_key = f"{artifact_id}/manifest.json"
    data = model.model_dump_json().encode("utf-8")
    content_hash = await asyncio.to_thread(store.put, object_key, data)
    updated = await artifacts.update_content(
        artifact_id,
        content_hash=content_hash,
        object_key=object_key,
        meta=meta,
        merge_meta=True,
    )
    if updated is None:
        raise LookupError("artifact not found")
    return updated

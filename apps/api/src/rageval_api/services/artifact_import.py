"""Copy artifacts from one project into another (new IDs, remapped parents)."""

from __future__ import annotations

import json
from typing import Any

from rageval_api.services.artifact_meta import counts_from_payload
from rageval_api.services.artifact_naming import naming_meta, source_name_from_record
from rageval_domain import ArtifactType, new_id
from rageval_domain.ids import IdPrefix
from rageval_metadb_sqlite.repositories import ArtifactRecord, ArtifactRepository
from rageval_storage_fs import FileSystemObjectStore

IMPORTABLE_TYPES = frozenset(
    {
        ArtifactType.RAW_BUNDLE.value,
        ArtifactType.CLEAN_CORPUS.value,
        ArtifactType.CHUNK_SET.value,
        ArtifactType.TEST_SET.value,
    }
)

_TYPE_PREFIX: dict[str, IdPrefix] = {
    ArtifactType.RAW_BUNDLE.value: "raw",
    ArtifactType.CLEAN_CORPUS.value: "clean",
    ArtifactType.CHUNK_SET.value: "chunks",
    ArtifactType.TEST_SET.value: "test",
}


class ArtifactImportError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _topo_sort(records: dict[str, ArtifactRecord]) -> list[str]:
    """Parents before children among the selected set."""
    pending = set(records)
    ordered: list[str] = []
    while pending:
        ready = [
            aid
            for aid in pending
            if not any(p in pending for p in records[aid].parent_ids)
        ]
        if not ready:
            # Cycle or self-ref within selection — fall back to stable order.
            ready = sorted(pending)
        for aid in sorted(ready):
            pending.remove(aid)
            ordered.append(aid)
    return ordered


def _collect_with_parents(
    artifacts: dict[str, ArtifactRecord],
    seed_ids: list[str],
    *,
    include_parents: bool,
) -> dict[str, ArtifactRecord]:
    selected: dict[str, ArtifactRecord] = {}
    stack = list(seed_ids)
    while stack:
        aid = stack.pop()
        if aid in selected:
            continue
        record = artifacts.get(aid)
        if record is None:
            raise ArtifactImportError(f"artifact not found: {aid}", status_code=404)
        if record.type not in IMPORTABLE_TYPES:
            raise ArtifactImportError(
                f"artifact type not importable: {record.type} ({aid})"
            )
        selected[aid] = record
        if include_parents:
            for parent_id in record.parent_ids:
                if parent_id not in selected:
                    stack.append(parent_id)
    return selected


async def import_artifacts_from_project(
    *,
    target_project_id: str,
    source_project_id: str,
    artifact_ids: list[str],
    include_parents: bool,
    artifacts: ArtifactRepository,
    store: FileSystemObjectStore,
) -> tuple[list[ArtifactRecord], dict[str, str]]:
    if not artifact_ids:
        raise ArtifactImportError("at least one artifact_id required")
    if source_project_id == target_project_id:
        raise ArtifactImportError("source_project_id must differ from target project")

    source_rows = await artifacts.list_for_project(source_project_id)
    source_by_id = {r.id: r for r in source_rows}
    for aid in artifact_ids:
        if aid not in source_by_id:
            raise ArtifactImportError(
                f"artifact {aid} not found in source project",
                status_code=404,
            )

    selected = _collect_with_parents(
        source_by_id,
        artifact_ids,
        include_parents=include_parents,
    )
    for record in selected.values():
        if record.project_id != source_project_id:
            raise ArtifactImportError(
                f"artifact {record.id} belongs to another project",
                status_code=400,
            )

    id_map: dict[str, str] = {
        old_id: new_id(_TYPE_PREFIX[rec.type]) for old_id, rec in selected.items()
    }
    created: list[ArtifactRecord] = []

    for old_id in _topo_sort(selected):
        record = selected[old_id]
        new_artifact_id = id_map[old_id]
        created.append(
            await _copy_one(
                record=record,
                new_artifact_id=new_artifact_id,
                target_project_id=target_project_id,
                id_map=id_map,
                artifacts=artifacts,
                store=store,
            )
        )

    return created, id_map


async def _copy_one(
    *,
    record: ArtifactRecord,
    new_artifact_id: str,
    target_project_id: str,
    id_map: dict[str, str],
    artifacts: ArtifactRepository,
    store: FileSystemObjectStore,
) -> ArtifactRecord:
    if not record.object_key:
        raise ArtifactImportError(f"artifact has no object_key: {record.id}")

    payload: dict[str, Any] = json.loads(store.get(record.object_key).decode("utf-8"))
    payload["id"] = new_artifact_id
    payload["project_id"] = target_project_id

    old_parents = list(payload.get("parent_ids") or record.parent_ids or [])
    payload["parent_ids"] = [id_map[p] for p in old_parents if p in id_map]

    if record.type == ArtifactType.RAW_BUNDLE.value:
        files = payload.get("files") or []
        for file_ref in files:
            old_path = file_ref.get("path")
            if not old_path:
                continue
            data = store.get(old_path)
            name = file_ref.get("original_name") or old_path.rsplit("/", 1)[-1]
            new_path = f"{new_artifact_id}/files/{name}"
            store.put(new_path, data)
            file_ref["path"] = new_path

    if record.type == ArtifactType.INDEX_RUN.value and "chunk_set_id" in payload:
        mapped = id_map.get(payload["chunk_set_id"])
        if mapped:
            payload["chunk_set_id"] = mapped

    meta = dict(record.meta or {})
    meta.update(counts_from_payload(record.type, payload))
    source = source_name_from_record(record)
    meta.update(naming_meta(record.type, source))
    meta["imported_from"] = {
        "project_id": record.project_id,
        "artifact_id": record.id,
    }

    if record.type == ArtifactType.CHUNK_SET.value and meta.get("chunk_count", 0) == 0:
        raise ArtifactImportError(
            f"refusing to import empty chunk_set {record.id} (0 chunks in manifest)"
        )
    if record.type == ArtifactType.TEST_SET.value and meta.get("query_count", 0) == 0:
        raise ArtifactImportError(
            f"refusing to import empty test_set {record.id} (0 queries in manifest)"
        )

    object_key = f"{new_artifact_id}/manifest.json"
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    content_hash = store.put(object_key, data)

    return await artifacts.create(
        artifact_id=new_artifact_id,
        project_id=target_project_id,
        artifact_type=record.type,
        parent_ids=payload["parent_ids"],
        content_hash=content_hash,
        object_key=object_key,
        meta=meta,
    )

"""Delete artifacts from MetaDB + object store."""

from __future__ import annotations

import asyncio
from typing import Any

from rageval_domain import ArtifactType, IndexRun
from rageval_metadb_sqlite.experiment_repo import ExperimentRepository
from rageval_metadb_sqlite.repositories import ArtifactRecord, ArtifactRepository
from rageval_storage_fs import FileSystemObjectStore
from rageval_vectordb_qdrant import QdrantVectorStore


class ArtifactDeleteError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


async def _collect_descendants(
    root_id: str,
    *,
    project_id: str,
    artifacts: ArtifactRepository,
) -> list[str]:
    """Return descendant artifact ids (children before parents / leaf-first)."""
    project_rows = await artifacts.list_for_project(project_id)
    children: dict[str, list[str]] = {r.id: [] for r in project_rows}
    for row in project_rows:
        for parent_id in row.parent_ids:
            if parent_id in children:
                children[parent_id].append(row.id)

    ordered: list[str] = []
    seen: set[str] = set()

    def visit(aid: str) -> None:
        if aid in seen or aid not in children:
            return
        for child_id in children[aid]:
            visit(child_id)
        if aid != root_id:
            seen.add(aid)
            ordered.append(aid)

    visit(root_id)
    return ordered


def _blocking_run_ids(runs: list[Any], artifact_id: str) -> list[str]:
    return [
        run.id
        for run in runs
        if run.start_artifact_id == artifact_id or run.test_set_id == artifact_id
    ]


def _raise_if_blocking_runs(runs: list[Any], artifact_id: str, *, label: str = "artifact") -> None:
    blocking = _blocking_run_ids(runs, artifact_id)
    if not blocking:
        return
    raise ArtifactDeleteError(
        f"{label} is referenced by experiment runs: "
        + ", ".join(blocking[:8])
        + ("…" if len(blocking) > 8 else ""),
        status_code=409,
    )


async def _resolve_delete_ids(
    *,
    artifact_id: str,
    cascade: bool,
    record: ArtifactRecord,
    runs: list[Any],
    artifacts: ArtifactRepository,
) -> list[str]:
    _raise_if_blocking_runs(runs, artifact_id)

    dependents = await artifacts.list_dependents(
        artifact_id, project_id=record.project_id
    )
    if dependents and not cascade:
        ids = ", ".join(d.id for d in dependents[:8])
        more = "…" if len(dependents) > 8 else ""
        raise ArtifactDeleteError(
            f"artifact has {len(dependents)} dependent artifact(s): {ids}{more}. "
            "Retry with cascade=true to delete them too.",
            status_code=409,
        )

    to_delete: list[str] = []
    if cascade:
        to_delete.extend(
            await _collect_descendants(
                artifact_id,
                project_id=record.project_id,
                artifacts=artifacts,
            )
        )
        for dep_id in to_delete:
            _raise_if_blocking_runs(
                runs,
                dep_id,
                label=f"dependent artifact {dep_id}",
            )
    to_delete.append(artifact_id)
    return to_delete


async def _delete_index_run_collection(
    row: ArtifactRecord,
    *,
    store: FileSystemObjectStore,
    vector_store: QdrantVectorStore,
) -> None:
    if row.type != ArtifactType.INDEX_RUN.value or not row.object_key:
        return
    try:
        payload = await asyncio.to_thread(store.get, row.object_key)
        index_run = IndexRun.model_validate_json(payload)
        await asyncio.to_thread(
            vector_store.delete_collection,
            index_run.collection_name,
        )
    except (FileNotFoundError, ValueError):
        pass


async def _delete_one_artifact(
    aid: str,
    *,
    artifacts: ArtifactRepository,
    store: FileSystemObjectStore,
    vector_store: QdrantVectorStore | None,
) -> str | None:
    row: ArtifactRecord | None = await artifacts.get(aid)
    if row is None:
        return None
    if vector_store is not None:
        await _delete_index_run_collection(row, store=store, vector_store=vector_store)
    await asyncio.to_thread(store.delete_prefix, aid)
    await artifacts.delete(aid)
    return aid


async def delete_artifact(
    *,
    artifact_id: str,
    cascade: bool,
    artifacts: ArtifactRepository,
    experiments: ExperimentRepository,
    store: FileSystemObjectStore,
    vector_store: QdrantVectorStore | None = None,
) -> list[str]:
    record = await artifacts.get(artifact_id)
    if record is None:
        raise ArtifactDeleteError("artifact not found", status_code=404)

    runs = await experiments.list_for_project(record.project_id, with_metrics=False)
    to_delete = await _resolve_delete_ids(
        artifact_id=artifact_id,
        cascade=cascade,
        record=record,
        runs=runs,
        artifacts=artifacts,
    )

    deleted: list[str] = []
    for aid in to_delete:
        removed = await _delete_one_artifact(
            aid,
            artifacts=artifacts,
            store=store,
            vector_store=vector_store,
        )
        if removed is not None:
            deleted.append(removed)
    return deleted

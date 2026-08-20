"""Derive display meta (counts, empty reasons) from stored manifests."""

from __future__ import annotations

import json
from typing import Any

from rageval_api.services.artifact_naming import display_name, resolve_source_name
from rageval_api.services.chunk_length_stats import length_chars_from_chunks
from rageval_domain import ArtifactType
from rageval_metadb_sqlite.repositories import ArtifactRecord, ArtifactRepository
from rageval_storage_fs import FileSystemObjectStore


def _load_payload(
    store: FileSystemObjectStore,
    object_key: str | None,
) -> dict[str, Any] | None:
    if not object_key:
        return None
    try:
        return json.loads(store.get(object_key).decode("utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def counts_from_payload(artifact_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if artifact_type == ArtifactType.CHUNK_SET.value:
        chunks = payload.get("chunks") or []
        out: dict[str, Any] = {"chunk_count": len(chunks)}
        length_chars = length_chars_from_chunks(chunks)
        if length_chars:
            out["length_chars"] = length_chars
        return out
    if artifact_type == ArtifactType.TEST_SET.value:
        return {"query_count": len(payload.get("queries") or [])}
    if artifact_type == ArtifactType.CLEAN_CORPUS.value:
        return {"document_count": len(payload.get("documents") or [])}
    if artifact_type == ArtifactType.RAW_BUNDLE.value:
        return {"file_count": len(payload.get("files") or [])}
    return {}


def _diagnose_from_clean_corpus_parent(
    *,
    parent: ArtifactRecord,
    record: ArtifactRecord,
    store: FileSystemObjectStore,
) -> str | None:
    parent_payload = _load_payload(store, parent.object_key)
    if parent_payload is None:
        return (
            "0 chunks: parent clean_corpus manifest is missing from object store "
            f"({parent.id})"
        )
    docs = parent_payload.get("documents") or []
    if not docs:
        return (
            "0 chunks: parent clean_corpus has 0 documents "
            "(prep extracted nothing — check raw files / pipeline)"
        )
    nonempty = [
        d
        for d in docs
        if isinstance(d, dict) and str(d.get("text") or "").strip()
    ]
    if not nonempty:
        return (
            f"0 chunks: parent clean_corpus has {len(docs)} document(s) "
            "but all text is empty/whitespace"
        )
    size = (record.meta or {}).get("size")
    overlap = (record.meta or {}).get("overlap")
    hint = ""
    if size is not None:
        hint = f" (chunker size={size}, overlap={overlap})"
    return (
        f"0 chunks: chunker produced nothing from {len(nonempty)} "
        f"non-empty document(s){hint}"
    )


def _diagnose_imported_empty(record: ArtifactRecord) -> str | None:
    imported = (record.meta or {}).get("imported_from")
    if isinstance(imported, dict) and imported.get("artifact_id"):
        return (
            "0 chunks: imported chunk_set is empty "
            f"(source {imported.get('artifact_id')} had no chunks, or copy failed)"
        )
    return None


def diagnose_empty_chunk_set(
    *,
    payload: dict[str, Any],
    record: ArtifactRecord,
    store: FileSystemObjectStore,
    parent_records: list[ArtifactRecord],
) -> str:
    """Human-readable reason why a chunk_set has zero chunks."""
    chunks = payload.get("chunks") or []
    if chunks:
        return ""

    for parent in parent_records:
        if parent.type != ArtifactType.CLEAN_CORPUS.value:
            continue
        reason = _diagnose_from_clean_corpus_parent(
            parent=parent, record=record, store=store
        )
        if reason is not None:
            return reason

    imported_reason = _diagnose_imported_empty(record)
    if imported_reason is not None:
        return imported_reason

    if not record.parent_ids:
        return "0 chunks: chunk_set has no chunks and no parent corpus to inspect"

    return "0 chunks: chunk_set manifest has an empty chunks list"


async def enrich_meta(
    record: ArtifactRecord,
    store: FileSystemObjectStore,
    artifacts: ArtifactRepository | None = None,
) -> dict[str, Any]:
    """Return meta with counts synced from manifest and empty_reason when needed."""
    meta: dict[str, Any] = dict(record.meta or {})
    payload = _load_payload(store, record.object_key)

    def load_payload(object_key: str) -> dict[str, Any] | None:
        return _load_payload(store, object_key)

    if payload is None:
        if record.object_key:
            meta["issues"] = ["manifest missing from object store"]
            if record.type == ArtifactType.CHUNK_SET.value:
                meta["chunk_count"] = meta.get("chunk_count", 0)
                meta["empty_reason"] = "manifest missing from object store"
        source = await resolve_source_name(
            record,
            payload=None,
            artifacts=artifacts,
            load_payload=load_payload,
        )
        if source:
            meta["source_name"] = source
            meta["display_name"] = display_name(record.type, source)
        return meta

    meta.update(counts_from_payload(record.type, payload))

    source = await resolve_source_name(
        record,
        payload=payload,
        artifacts=artifacts,
        load_payload=load_payload,
    )
    if source:
        meta["source_name"] = source
        meta["display_name"] = display_name(record.type, source)

    if record.type == ArtifactType.CHUNK_SET.value and meta.get("chunk_count") == 0:
        parents: list[ArtifactRecord] = []
        if artifacts is not None:
            for pid in record.parent_ids:
                parent = await artifacts.get(pid)
                if parent is not None:
                    parents.append(parent)
        reason = diagnose_empty_chunk_set(
            payload=payload,
            record=record,
            store=store,
            parent_records=parents,
        )
        if reason:
            meta["empty_reason"] = reason
            meta["issues"] = [reason]
    elif "empty_reason" in meta and meta.get("chunk_count", 0) > 0:
        meta.pop("empty_reason", None)

    return meta


def diagnose_empty_corpus(corpus_documents: list[Any]) -> str:
    if not corpus_documents:
        return (
            "chunker produced 0 chunks: clean_corpus has 0 documents "
            "(prep extracted nothing)"
        )
    nonempty = [
        d
        for d in corpus_documents
        if str(getattr(d, "text", "") or "").strip()
    ]
    if not nonempty:
        return (
            f"chunker produced 0 chunks: clean_corpus has {len(corpus_documents)} "
            "document(s) but all text is empty/whitespace"
        )
    return (
        f"chunker produced 0 chunks from {len(nonempty)} non-empty document(s)"
    )

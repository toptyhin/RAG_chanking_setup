"""Human-readable artifact source names derived from uploaded documents."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Any

from rageval_domain import ArtifactType
from rageval_metadb_sqlite.repositories import ArtifactRecord, ArtifactRepository

# Display prefix before underscore (matches user-facing TYPE_name pattern).
TYPE_PREFIX: dict[str, str] = {
    ArtifactType.RAW_BUNDLE.value: "raw",
    ArtifactType.CLEAN_CORPUS.value: "clean",
    ArtifactType.CHUNK_SET.value: "chunks",
    ArtifactType.TEST_SET.value: "test",
    ArtifactType.INDEX_RUN.value: "index",
    ArtifactType.EXPERIMENT_RUN.value: "run",
    ArtifactType.EVAL_REPORT.value: "report",
}


def source_name_from_filename(filename: str | None) -> str:
    """Turn 'Устав несения службы.pdf' → 'Устав_несения_службы'."""
    raw = PurePosixPath(filename or "unnamed").name
    stem = PurePosixPath(raw).stem or "unnamed"
    # Spaces / punctuation → underscore; keep letters (incl. Cyrillic), digits, - _
    cleaned = re.sub(r"\s+", "_", stem.strip())
    cleaned = re.sub(r"[^\w\-]+", "_", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unnamed"


def source_name_from_filenames(filenames: list[str]) -> str:
    if not filenames:
        return "unnamed"
    primary = source_name_from_filename(filenames[0])
    if len(filenames) == 1:
        return primary
    return f"{primary}_+{len(filenames) - 1}"


def source_name_from_raw_payload(payload: dict[str, Any]) -> str | None:
    files = payload.get("files") or []
    names = [
        str(f.get("original_name"))
        for f in files
        if isinstance(f, dict) and f.get("original_name")
    ]
    if not names:
        return None
    return source_name_from_filenames(names)


def source_name_from_clean_payload(payload: dict[str, Any]) -> str | None:
    docs = payload.get("documents") or []
    names: list[str] = []
    seen: set[str] = set()
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        path = doc.get("source_path")
        if not path:
            continue
        stem = source_name_from_filename(str(path))
        if stem not in seen:
            seen.add(stem)
            names.append(str(path))
    if not names:
        return None
    return source_name_from_filenames(names)


def _source_from_payload(
    artifact_type: str, payload: dict[str, Any] | None
) -> str | None:
    if payload is None:
        return None
    if artifact_type == ArtifactType.RAW_BUNDLE.value:
        return source_name_from_raw_payload(payload)
    if artifact_type == ArtifactType.CLEAN_CORPUS.value:
        return source_name_from_clean_payload(payload)
    return None


async def resolve_source_name(
    record: ArtifactRecord,
    *,
    payload: dict[str, Any] | None,
    artifacts: ArtifactRepository | None,
    load_payload: Callable[[str], dict[str, Any] | None] | None = None,
) -> str | None:
    """Prefer stored meta, then payload, then walk parent artifacts."""
    meta = record.meta or {}
    existing = meta.get("source_name")
    if isinstance(existing, str) and existing.strip():
        return existing.strip()

    derived = _source_from_payload(record.type, payload)
    if derived:
        return derived

    if artifacts is None:
        return None

    for parent_id in record.parent_ids:
        parent = await artifacts.get(parent_id)
        if parent is None:
            continue
        parent_name = (parent.meta or {}).get("source_name")
        if isinstance(parent_name, str) and parent_name.strip():
            return parent_name.strip()
        if load_payload is not None and parent.object_key:
            parent_payload = load_payload(parent.object_key)
            from_parent = _source_from_payload(parent.type, parent_payload)
            if from_parent:
                return from_parent

    return None


def display_name(artifact_type: str, source_name: str) -> str:
    prefix = TYPE_PREFIX.get(artifact_type, artifact_type)
    return f"{prefix}_{source_name}"


def naming_meta(artifact_type: str, source_name: str | None) -> dict[str, str]:
    if not source_name:
        return {}
    return {
        "source_name": source_name,
        "display_name": display_name(artifact_type, source_name),
    }


def source_name_from_record(record: ArtifactRecord | None) -> str | None:
    if record is None:
        return None
    value = (record.meta or {}).get("source_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None

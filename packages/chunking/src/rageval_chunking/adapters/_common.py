"""Shared helpers for chunker adapters."""

from __future__ import annotations

from typing import Any

from rageval_domain import Chunk, ChunkSet, CleanCorpus, content_id

from rageval_chunking.ids import stable_chunk_id, stable_chunk_id_by_index


def build_chunk_set(
    corpus: CleanCorpus,
    *,
    pipeline_id: str,
    chunks: list[Chunk],
    pipeline_meta: dict[str, Any],
) -> ChunkSet:
    return ChunkSet(
        id=content_id(
            "chunks",
            corpus.project_id,
            corpus.id,
            pipeline_id,
            pipeline_meta,
            [chunk.model_dump(mode="json") for chunk in chunks],
        ),
        project_id=corpus.project_id,
        parent_ids=[corpus.id],
        chunk_pipeline_id=pipeline_id,
        chunks=chunks,
        meta={"chunk_pipeline": {"id": pipeline_id, **pipeline_meta}},
    )


def make_chunk(
    *,
    doc_id: str,
    text: str,
    index: int,
    pipeline_id: str,
    start: int | None = None,
    end: int | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> Chunk:
    if start is not None and end is not None:
        chunk_id = stable_chunk_id(doc_id, start, end)
    else:
        chunk_id = stable_chunk_id_by_index(doc_id, index, text)
    meta: dict[str, Any] = {"index": index, "pipeline": pipeline_id}
    if extra_meta:
        meta.update(extra_meta)
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text=text,
        start_char=start,
        end_char=end,
        meta=meta,
    )


def locate_span(haystack: str, needle: str, search_from: int = 0) -> tuple[int, int] | None:
    """Find *needle* in *haystack* starting at *search_from*; return (start, end)."""
    if not needle:
        return None
    idx = haystack.find(needle, search_from)
    if idx < 0:
        idx = haystack.find(needle.strip(), search_from)
    if idx < 0:
        return None
    return idx, idx + len(needle)

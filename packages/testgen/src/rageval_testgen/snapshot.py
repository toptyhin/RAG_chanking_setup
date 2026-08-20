"""Map gold spans onto chunk_ids for a concrete chunk_set."""

from __future__ import annotations

from typing import Any

from rageval_domain import Chunk, ChunkSet

__all__ = ["chunk_ids_for_spans", "span_overlaps_chunk"]


def span_overlaps_chunk(chunk: Chunk, doc_id: str, start: int, end: int) -> bool:
    if chunk.doc_id != doc_id:
        return False
    if chunk.start_char is None or chunk.end_char is None:
        return False
    return chunk.start_char < end and chunk.end_char > start


def chunk_ids_for_spans(
    chunk_set: ChunkSet,
    spans: list[dict[str, Any]] | None,
) -> list[str]:
    """Return unique chunk_ids that overlap any span (order preserved)."""
    if not spans:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for span in spans:
        doc_id = str(span.get("doc_id", ""))
        try:
            start = int(span.get("start", 0))
            end = int(span.get("end", 0))
        except (TypeError, ValueError):
            continue
        if not doc_id or start >= end:
            continue
        for chunk in chunk_set.chunks:
            if not span_overlaps_chunk(chunk, doc_id, start, end):
                continue
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            out.append(chunk.chunk_id)
    return out

"""Map test_set anchors (chunk / doc / span) onto a concrete chunk_set."""

from __future__ import annotations

from dataclasses import dataclass

from rageval_domain import Chunk, ChunkSet, TestSet


def _span_overlap(chunk: Chunk, doc_id: str, start: int, end: int) -> bool:
    if chunk.doc_id != doc_id:
        return False
    if chunk.start_char is None or chunk.end_char is None:
        # Fall back to substring containment when offsets missing.
        return False
    return chunk.start_char < end and chunk.end_char > start


@dataclass(slots=True)
class RelevanceIndex:
    by_id: dict[str, Chunk]
    by_doc: dict[str, list[Chunk]]
    normalized_texts: list[tuple[str, str]]


def build_relevance_index(chunk_set: ChunkSet) -> RelevanceIndex:
    by_doc: dict[str, list[Chunk]] = {}
    for chunk in chunk_set.chunks:
        by_doc.setdefault(chunk.doc_id, []).append(chunk)
    return RelevanceIndex(
        by_id={chunk.chunk_id: chunk for chunk in chunk_set.chunks},
        by_doc=by_doc,
        normalized_texts=[
            (chunk.chunk_id, chunk.text.lower()) for chunk in chunk_set.chunks
        ],
    )


def _chunks_for_spans(index: RelevanceIndex, spans: list) -> list[str]:
    relevant: list[str] = []
    for span in spans:
        doc_id = str(span.get("doc_id", ""))
        try:
            start = int(span.get("start", 0))
            end = int(span.get("end", 0))
        except (TypeError, ValueError):
            continue
        for chunk in index.by_doc.get(doc_id, []):
            if _span_overlap(chunk, doc_id, start, end):
                relevant.append(chunk.chunk_id)
    return relevant


def resolve_relevance(
    test_set: TestSet,
    chunk_set: ChunkSet,
    *,
    index: RelevanceIndex | None = None,
) -> dict[str, list[str]]:
    """Return query_id → relevant chunk_ids for the given chunk_set.

    Precedence (spans-first):
    1. ``relevant_spans`` when they overlap the current chunk_set
    2. ``relevant_chunk_ids`` snapshot
    3. ``relevant_doc_ids``
    4. substring match of query text against chunk bodies
    """
    lookup = index or build_relevance_index(chunk_set)
    out: dict[str, list[str]] = {}

    for query in test_set.queries:
        relevant: list[str] = []
        if query.relevant_spans:
            relevant = _chunks_for_spans(lookup, query.relevant_spans)
        if not relevant and query.relevant_chunk_ids:
            relevant = [cid for cid in query.relevant_chunk_ids if cid in lookup.by_id]
        if not relevant and query.relevant_doc_ids:
            for doc_id in query.relevant_doc_ids:
                relevant.extend(
                    chunk.chunk_id for chunk in lookup.by_doc.get(doc_id, [])
                )

        # Prep/Chunk Lab: doc_ids are regenerated per pipeline — fall back to
        # substring match of the query text against chunk bodies.
        if not relevant and query.text.strip():
            needle = query.text.strip().lower()
            for chunk_id, normalized_text in lookup.normalized_texts:
                if needle in normalized_text:
                    relevant.append(chunk_id)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for cid in relevant:
            if cid not in seen:
                seen.add(cid)
                unique.append(cid)
        out[query.query_id] = unique
    return out


def resolve_relevance_grades(
    test_set: TestSet,
    chunk_set: ChunkSet,
    *,
    relevance: dict[str, list[str]] | None = None,
    index: RelevanceIndex | None = None,
) -> dict[str, dict[str, float]]:
    """Return query_id → {chunk_id: gain} for graded nDCG.

    Uses ``TestQuery.relevance_grades`` when present; otherwise binary gain=1
    for each resolved relevant chunk id.
    """
    lookup = index or build_relevance_index(chunk_set)
    binary = relevance or resolve_relevance(test_set, chunk_set, index=lookup)
    out: dict[str, dict[str, float]] = {}
    for query in test_set.queries:
        grades: dict[str, float] = {}
        if query.relevance_grades:
            for cid, gain in query.relevance_grades.items():
                if cid in lookup.by_id and float(gain) > 0:
                    grades[cid] = float(gain)
        if not grades:
            grades = {cid: 1.0 for cid in binary.get(query.query_id, [])}
        out[query.query_id] = grades
    return out

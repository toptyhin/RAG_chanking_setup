from __future__ import annotations

from rageval_domain import Chunk, ChunkSet, TestQuery, TestSet
from rageval_eval import resolve_relevance


def test_resolve_by_doc_ids() -> None:
    chunks = ChunkSet(
        project_id="p",
        chunks=[
            Chunk(chunk_id="c1", doc_id="d1", text="a", start_char=0, end_char=1),
            Chunk(chunk_id="c2", doc_id="d2", text="b", start_char=0, end_char=1),
        ],
    )
    test = TestSet(
        project_id="p",
        queries=[TestQuery(query_id="q1", text="x", relevant_doc_ids=["d1"])],
    )
    rel = resolve_relevance(test, chunks)
    assert rel["q1"] == ["c1"]


def test_resolve_by_spans() -> None:
    chunks = ChunkSet(
        project_id="p",
        chunks=[
            Chunk(chunk_id="c1", doc_id="d1", text="hello world", start_char=0, end_char=11),
            Chunk(chunk_id="c2", doc_id="d1", text="other", start_char=20, end_char=25),
        ],
    )
    test = TestSet(
        project_id="p",
        queries=[
            TestQuery(
                query_id="q1",
                text="x",
                relevant_spans=[{"doc_id": "d1", "start": 0, "end": 5}],
            )
        ],
    )
    rel = resolve_relevance(test, chunks)
    assert rel["q1"] == ["c1"]


def test_spans_first_over_stale_chunk_ids() -> None:
    """When spans map onto the new chunk_set, ignore stale chunk_id snapshot."""
    chunks = ChunkSet(
        project_id="p",
        chunks=[
            Chunk(chunk_id="new_a", doc_id="d1", text="hello", start_char=0, end_char=5),
            Chunk(chunk_id="new_b", doc_id="d1", text="world", start_char=6, end_char=11),
        ],
    )
    test = TestSet(
        project_id="p",
        queries=[
            TestQuery(
                query_id="q1",
                text="x",
                relevant_chunk_ids=["old_missing"],
                relevant_spans=[{"doc_id": "d1", "start": 6, "end": 11}],
            )
        ],
    )
    rel = resolve_relevance(test, chunks)
    assert rel["q1"] == ["new_b"]


def test_fallback_to_chunk_ids_when_spans_miss() -> None:
    chunks = ChunkSet(
        project_id="p",
        chunks=[
            Chunk(chunk_id="c1", doc_id="d1", text="hello", start_char=0, end_char=5),
        ],
    )
    test = TestSet(
        project_id="p",
        queries=[
            TestQuery(
                query_id="q1",
                text="x",
                relevant_chunk_ids=["c1"],
                # Span on another doc → no overlap → fall back to chunk ids
                relevant_spans=[{"doc_id": "other", "start": 0, "end": 10}],
            )
        ],
    )
    rel = resolve_relevance(test, chunks)
    assert rel["q1"] == ["c1"]

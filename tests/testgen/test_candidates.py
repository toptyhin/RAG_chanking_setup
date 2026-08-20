from __future__ import annotations

from rageval_domain import Chunk, ChunkSet
from rageval_testgen import chunk_ids_for_spans, evidence_candidates


def _chunk_set() -> ChunkSet:
    return ChunkSet(
        project_id="p",
        chunks=[
            Chunk(
                chunk_id="c1",
                doc_id="d1",
                text="Customers may return items within 30 days of purchase.",
                start_char=0,
                end_char=54,
            ),
            Chunk(
                chunk_id="c2",
                doc_id="d1",
                text="Support is available 9-18 on weekdays.",
                start_char=55,
                end_char=93,
            ),
            Chunk(
                chunk_id="c3",
                doc_id="d1",
                text="Warranty covers manufacturing defects for one year.",
                start_char=94,
                end_char=145,
            ),
            Chunk(
                chunk_id="c4",
                doc_id="d2",
                text="Unrelated shipping policy about crates.",
                start_char=0,
                end_char=40,
            ),
        ],
    )


def test_quote_candidates_ranked_first() -> None:
    cs = _chunk_set()
    cands = evidence_candidates(
        cs,
        question="How long is the return window?",
        expected_answer="30 days",
        source_quote="Customers may return items within 30 days of purchase.",
        limit=10,
    )
    assert cands
    assert cands[0].chunk_id == "c1"
    assert cands[0].reason == "quote"


def test_neighbors_included() -> None:
    cs = _chunk_set()
    cands = evidence_candidates(
        cs,
        question="return window",
        source_quote="Customers may return items within 30 days of purchase.",
        limit=20,
    )
    ids = {c.chunk_id for c in cands}
    assert "c1" in ids
    # c2 is neighbor of c1 in same doc
    assert "c2" in ids
    neighbor = next(c for c in cands if c.chunk_id == "c2")
    assert neighbor.reason in {"neighbor", "bm25", "quote"}


def test_chunk_ids_for_spans() -> None:
    cs = _chunk_set()
    ids = chunk_ids_for_spans(
        cs,
        [{"doc_id": "d1", "start": 0, "end": 20}],
    )
    assert ids == ["c1"]


def test_chunk_ids_for_spans_skips_missing_offsets() -> None:
    cs = ChunkSet(
        project_id="p",
        chunks=[Chunk(chunk_id="x", doc_id="d1", text="hello")],
    )
    assert chunk_ids_for_spans(cs, [{"doc_id": "d1", "start": 0, "end": 5}]) == []

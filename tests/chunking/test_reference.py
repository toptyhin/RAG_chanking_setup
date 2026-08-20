"""Reference chunker tests."""

from __future__ import annotations

from rageval_chunking import chunk_fixed_size
from rageval_domain import CleanCorpus, CleanDocument


def test_fixed_size_chunks_stable_ids() -> None:
    corpus = CleanCorpus(
        project_id="proj_1",
        documents=[CleanDocument(doc_id="doc_a", text="abcdefghij" * 10)],  # 100 chars
    )
    a = chunk_fixed_size(corpus, size=20, overlap=5)
    b = chunk_fixed_size(corpus, size=20, overlap=5)
    assert len(a.chunks) >= 2
    assert a.id == b.id
    assert [c.chunk_id for c in a.chunks] == [c.chunk_id for c in b.chunks]
    assert all(c.doc_id == "doc_a" for c in a.chunks)
    assert a.chunk_pipeline_id == "reference_fixed"

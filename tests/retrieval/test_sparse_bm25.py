"""Sparse BM25 unit tests."""

from __future__ import annotations

from pathlib import Path

from rageval_domain import Chunk, ChunkSet, TestQuery, TestSet
from rageval_retrieval import SparseBm25Index, sparse_retrieve


def _fixture_chunk_set() -> ChunkSet:
    return ChunkSet(
        id="chunks_bm25",
        project_id="proj",
        chunks=[
            Chunk(chunk_id="c_alpha", doc_id="d1", text="ordinary background text about cats"),
            Chunk(
                chunk_id="c_target",
                doc_id="d1",
                text="contains UNIQUEKEYWORDXYZ for exact lexical match",
            ),
            Chunk(chunk_id="c_other", doc_id="d2", text="unrelated shipping invoice details"),
        ],
    )


def test_bm25_exact_term_finds_chunk(tmp_path: Path) -> None:
    chunk_set = _fixture_chunk_set()
    index = SparseBm25Index.build(chunk_set, index_dir=tmp_path / "bm25")
    hits = index.search("UNIQUEKEYWORDXYZ", top_k=2)
    assert hits
    assert hits[0][0] == "c_target"

    loaded = SparseBm25Index.load(tmp_path / "bm25")
    hits2 = loaded.search("UNIQUEKEYWORDXYZ", top_k=1)
    assert hits2[0][0] == "c_target"


def test_sparse_retrieve_ranks_target() -> None:
    chunk_set = _fixture_chunk_set()
    index = SparseBm25Index.build(chunk_set)
    test_set = TestSet(
        id="test_bm25",
        project_id="proj",
        queries=[
            TestQuery(
                query_id="q1",
                text="UNIQUEKEYWORDXYZ",
                relevant_chunk_ids=["c_target"],
            )
        ],
    )
    result = sparse_retrieve(test_set, index=index, top_k=3)
    assert result.results[0].ranked_chunk_ids[0] == "c_target"

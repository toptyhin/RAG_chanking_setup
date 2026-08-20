"""Stages 58–60 eval metrics: answer coverage, graded nDCG, no-answer."""

from __future__ import annotations

import math

from rageval_domain import Chunk, ChunkSet, TestQuery, TestSet
from rageval_eval import (
    answer_coverage_at_k,
    ndcg_at_k,
    resolve_relevance_grades,
    score_retrieval,
)


def test_answer_coverage_hit_and_miss() -> None:
    assert answer_coverage_at_k("forty two", ["the answer is forty two today"]) == 1.0
    assert answer_coverage_at_k("forty two", ["unrelated text about weather"]) == 0.0


def test_graded_ndcg_prefers_primary() -> None:
    grades = {"a": 2.0, "b": 1.0}
    good = ndcg_at_k(grades, ["a", "b"], 2)
    bad = ndcg_at_k(grades, ["b", "a"], 2)
    assert good > bad
    assert abs(good - 1.0) < 1e-9


def test_binary_ndcg_unchanged() -> None:
    relevant = ["a"]
    ranked = ["a", "b", "c"]
    assert ndcg_at_k(relevant, ranked, 3) == 1.0
    ranked_late = ["b", "a"]
    expected = (1.0 / math.log2(3)) / (1.0 / math.log2(2))
    assert abs(ndcg_at_k(relevant, ranked_late, 2) - expected) < 1e-9


def test_resolve_relevance_grades() -> None:
    chunks = ChunkSet(
        project_id="p",
        chunks=[
            Chunk(chunk_id="c1", doc_id="d1", text="a"),
            Chunk(chunk_id="c2", doc_id="d1", text="b"),
        ],
    )
    test = TestSet(
        project_id="p",
        queries=[
            TestQuery(
                query_id="q1",
                text="x",
                relevant_chunk_ids=["c1", "c2"],
                relevance_grades={"c1": 2.0, "c2": 1.0},
            )
        ],
    )
    grades = resolve_relevance_grades(test, chunks)
    assert grades["q1"] == {"c1": 2.0, "c2": 1.0}


def test_no_answer_uses_abstention_not_recall() -> None:
    relevance = {"q1": ["a"], "q2": []}
    ranked = {"q1": ["a"], "q2": ["x", "y"]}
    test = TestSet(
        project_id="p",
        queries=[
            TestQuery(query_id="q1", text="fact", relevant_chunk_ids=["a"], query_type="factoid"),
            TestQuery(query_id="q2", text="missing", relevant_chunk_ids=[], query_type="no-answer"),
        ],
    )
    scores = score_retrieval(relevance, ranked, ks=(1, 5), test_set=test)
    # Only factoid contributes to recall → perfect.
    assert scores["recall@1"] == 1.0
    assert scores["abstention@1"] == 0.0  # returned junk for no-answer
    assert "by_query_type" in scores
    assert scores["by_query_type"]["factoid.recall@1"] == 1.0


def test_no_answer_abstention_success() -> None:
    relevance = {"q1": []}
    ranked = {"q1": []}
    test = TestSet(
        project_id="p",
        queries=[
            TestQuery(query_id="q1", text="missing", relevant_chunk_ids=[], query_type="no-answer"),
        ],
    )
    scores = score_retrieval(relevance, ranked, ks=(5,), test_set=test)
    assert scores.get("abstention@5") == 1.0
    assert scores["mrr"] == 0.0


def test_by_query_type_from_meta_level() -> None:
    """Saved LLM ``meta.level`` still drives breakdown when query_type is empty."""
    relevance = {"q1": ["a"], "q2": ["b"]}
    ranked = {"q1": ["a"], "q2": ["x"]}
    test = TestSet(
        project_id="p",
        queries=[
            TestQuery(
                query_id="q1",
                text="easy",
                relevant_chunk_ids=["a"],
                meta={"level": "L1"},
            ),
            TestQuery(
                query_id="q2",
                text="hard",
                relevant_chunk_ids=["b"],
                meta={"level": "L3"},
            ),
        ],
    )
    scores = score_retrieval(relevance, ranked, ks=(1,), test_set=test)
    breakdown = scores["by_query_type"]
    assert breakdown["l1.recall@1"] == 1.0
    assert breakdown["l3.recall@1"] == 0.0

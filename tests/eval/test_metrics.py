"""Unit tests for Recall / nDCG / MRR."""

from __future__ import annotations

import math

from rageval_eval import mrr, ndcg_at_k, recall_at_k, score_retrieval


def test_recall_at_k_known_fixture() -> None:
    relevant = ["a", "b"]
    ranked = ["x", "a", "y", "b", "z"]
    assert recall_at_k(relevant, ranked, 1) == 0.0
    assert recall_at_k(relevant, ranked, 2) == 0.5
    assert recall_at_k(relevant, ranked, 5) == 1.0


def test_ndcg_at_k_known_fixture() -> None:
    relevant = ["a"]
    ranked = ["a", "b", "c"]
    # DCG = 1/log2(2) = 1, IDCG = 1 → nDCG@3 = 1
    assert ndcg_at_k(relevant, ranked, 3) == 1.0

    ranked_late = ["b", "a"]
    expected = (1.0 / math.log2(3)) / (1.0 / math.log2(2))
    assert abs(ndcg_at_k(relevant, ranked_late, 2) - expected) < 1e-9


def test_mrr_known_fixture() -> None:
    assert mrr(["a"], ["x", "a", "y"]) == 0.5
    assert mrr(["a"], ["a"]) == 1.0
    assert mrr(["a"], ["x", "y"]) == 0.0


def test_score_retrieval_aggregate() -> None:
    relevance = {"q1": ["a"], "q2": ["b"]}
    ranked = {"q1": ["a"], "q2": ["x", "b"]}
    scores = score_retrieval(relevance, ranked, ks=(1, 5))
    assert scores["recall@1"] == 0.5
    assert scores["mrr"] == 0.75

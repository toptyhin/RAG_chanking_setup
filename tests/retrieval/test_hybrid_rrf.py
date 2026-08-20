"""Hybrid RRF unit tests."""

from __future__ import annotations

from rageval_retrieval import rrf_fuse


def test_rrf_prefers_shared_top() -> None:
    dense = ["a", "b", "c"]
    sparse = ["c", "a", "d"]
    fused, scores = rrf_fuse([dense, sparse], top_k=3, k=60)
    assert fused[0] == "a"
    assert scores[0] > scores[1]
    assert set(fused) <= {"a", "b", "c", "d"}


def test_rrf_respects_top_k() -> None:
    fused, _ = rrf_fuse([["x", "y", "z"], ["z", "y"]], top_k=2)
    assert len(fused) == 2

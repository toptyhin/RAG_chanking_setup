"""Orchestrator retrieval-mode axis coverage."""

from __future__ import annotations

from rageval_orchestrator import expand_grid


def test_hybrid_mode_in_swept_grid() -> None:
    points = expand_grid(
        {"retrieval.top_k": 5},
        {"retrieval.mode": ["dense", "hybrid"]},
    )
    modes = {p["retrieval.mode"] for p in points}
    assert modes == {"dense", "hybrid"}
    assert all(p["retrieval.top_k"] == 5 for p in points)

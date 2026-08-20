"""Pareto front unit tests (stage 47)."""

from __future__ import annotations

from rageval_optimize import MetricsPoint, pareto_front


def test_pareto_front_five_synthetic_points() -> None:
    # Axes: recall ↑, latency ↓, index_size ↓
    points = [
        MetricsPoint(0, recall=0.9, latency_p95_ms=100, index_size_mb=10, config={"a": 0}, metrics={}),
        MetricsPoint(1, recall=0.8, latency_p95_ms=50, index_size_mb=10, config={"a": 1}, metrics={}),
        MetricsPoint(2, recall=0.7, latency_p95_ms=40, index_size_mb=5, config={"a": 2}, metrics={}),
        MetricsPoint(3, recall=0.85, latency_p95_ms=90, index_size_mb=8, config={"a": 3}, metrics={}),
        # Dominated by #0 (worse recall, higher latency, larger size)
        MetricsPoint(4, recall=0.6, latency_p95_ms=120, index_size_mb=12, config={"a": 4}, metrics={}),
    ]
    front = pareto_front(points)
    idxs = sorted(p.point_index for p in front)
    assert 4 not in idxs
    assert 0 in idxs
    assert 1 in idxs
    assert 2 in idxs
    # #3: recall 0.85 < 0.9, latency 90 < 100, size 8 < 10 — not dominated by #0
    # vs #1: higher recall, higher latency, smaller size — tradeoff
    assert 3 in idxs
    assert len(front) == 4


def test_single_point_is_front() -> None:
    p = MetricsPoint(0, 1.0, 1.0, 1.0, {}, {})
    assert pareto_front([p]) == [p]

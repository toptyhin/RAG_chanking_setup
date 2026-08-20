"""Pareto front over recall ↑, latency_p95 ↓, index_size ↓."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MetricsPoint:
    point_index: int
    recall: float
    latency_p95_ms: float
    index_size_mb: float
    config: dict[str, Any]
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "point_index": self.point_index,
            "recall": self.recall,
            "latency_p95_ms": self.latency_p95_ms,
            "index_size_mb": self.index_size_mb,
            "config": self.config,
            "metrics": self.metrics,
        }


def _dominates(a: MetricsPoint, b: MetricsPoint) -> bool:
    """True if ``a`` is at least as good on all axes and strictly better on one."""
    ge_all = (
        a.recall >= b.recall
        and a.latency_p95_ms <= b.latency_p95_ms
        and a.index_size_mb <= b.index_size_mb
    )
    gt_one = (
        a.recall > b.recall
        or a.latency_p95_ms < b.latency_p95_ms
        or a.index_size_mb < b.index_size_mb
    )
    return ge_all and gt_one


def pareto_front(points: list[MetricsPoint]) -> list[MetricsPoint]:
    """Return non-dominated points (order preserved)."""
    front: list[MetricsPoint] = []
    for candidate in points:
        if any(_dominates(other, candidate) for other in points if other is not candidate):
            continue
        front.append(candidate)
    return front


def recall_from_metrics(metrics: dict[str, Any]) -> float:
    for key in ("recall@10", "recall@5", "recall@1"):
        if key in metrics and metrics[key] is not None:
            return float(metrics[key])
    return 0.0


def index_size_from_metrics(metrics: dict[str, Any]) -> float:
    for key in ("index_ram_mb", "index_disk_mb", "index_size_mb"):
        if key in metrics and metrics[key] is not None:
            return float(metrics[key])
    return 0.0


def points_from_rows(rows: list[Any]) -> list[MetricsPoint]:
    """Build points from experiment metrics row records / dict-like objects."""
    points: list[MetricsPoint] = []
    for row in rows:
        metrics = getattr(row, "metrics", None) or row.get("metrics", {})
        if isinstance(metrics, dict) and metrics.get("status") == "failed":
            continue
        config = getattr(row, "config", None) or row.get("config", {})
        point_index = getattr(row, "point_index", None)
        if point_index is None:
            point_index = row.get("point_index", 0)
        latency = getattr(row, "latency_p95_ms", None)
        if latency is None and isinstance(row, dict):
            latency = row.get("latency_p95_ms")
        points.append(
            MetricsPoint(
                point_index=int(point_index),
                recall=recall_from_metrics(metrics),
                latency_p95_ms=float(latency or 0.0),
                index_size_mb=index_size_from_metrics(metrics),
                config=dict(config),
                metrics=dict(metrics),
            )
        )
    return points

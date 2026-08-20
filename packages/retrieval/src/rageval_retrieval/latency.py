"""Latency aggregation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class LatencyStats:
    count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "mean_ms": self.mean_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
        }


def summarize_latencies(latencies_ms: list[float]) -> LatencyStats:
    if not latencies_ms:
        return LatencyStats(count=0, mean_ms=0.0, p50_ms=0.0, p95_ms=0.0)
    arr = np.asarray(latencies_ms, dtype=np.float64)
    return LatencyStats(
        count=len(latencies_ms),
        mean_ms=float(arr.mean()),
        p50_ms=float(np.percentile(arr, 50)),
        p95_ms=float(np.percentile(arr, 95)),
    )

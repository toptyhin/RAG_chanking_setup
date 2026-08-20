"""Expand fixed × swept into configuration points."""

from __future__ import annotations

from itertools import product
from typing import Any


def expand_grid(
    fixed: dict[str, Any],
    swept: dict[str, list[Any]],
    *,
    max_axes: int = 2,
) -> list[dict[str, Any]]:
    if len(swept) > max_axes:
        raise ValueError(f"at most {max_axes} swept axes allowed, got {len(swept)}")
    for key, values in swept.items():
        if not isinstance(values, list) or not values:
            raise ValueError(f"swept[{key!r}] must be a non-empty list")

    if not swept:
        return [dict(fixed)]

    keys = list(swept.keys())
    points: list[dict[str, Any]] = []
    for combo in product(*(swept[k] for k in keys)):
        point = dict(fixed)
        for key, value in zip(keys, combo, strict=True):
            point[key] = value
        points.append(point)
    return points

"""Grid expansion unit tests."""

from __future__ import annotations

import pytest

from rageval_orchestrator import expand_grid


def test_expand_empty_swept() -> None:
    assert expand_grid({"a": 1}, {}) == [{"a": 1}]


def test_expand_two_axes() -> None:
    points = expand_grid(
        {"fixed": True},
        {"retrieval.top_k": [5, 10], "embedding.dimension": [16, 32]},
    )
    assert len(points) == 4
    assert {"fixed": True, "retrieval.top_k": 5, "embedding.dimension": 16} in points


def test_expand_rejects_three_axes() -> None:
    with pytest.raises(ValueError):
        expand_grid({}, {"a": [1], "b": [1], "c": [1]})

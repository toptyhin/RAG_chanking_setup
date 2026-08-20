"""Quantization parsing and index config tests."""

from __future__ import annotations

import pytest

from rageval_vectordb_qdrant import parse_quantization_axis, quantization_to_qdrant


def test_parse_quantization_axis_forms() -> None:
    assert parse_quantization_axis(None) == (None, None)
    assert parse_quantization_axis("none") == (None, None)
    config, rescore = parse_quantization_axis("binary")
    assert config == {"method": "binary", "rescore": False}
    assert rescore is False
    config, rescore = parse_quantization_axis("binary+rescore")
    assert config["method"] == "binary"
    assert rescore is True
    config, rescore = parse_quantization_axis({"method": "binary", "rescore": True})
    assert config["method"] == "binary"
    assert rescore is True
    config, rescore = parse_quantization_axis("scalar")
    assert config["method"] == "scalar"
    assert rescore is False


def test_quantization_to_qdrant_binary() -> None:
    assert quantization_to_qdrant(None) is None
    q = quantization_to_qdrant({"method": "binary"})
    assert q is not None
    assert q.binary is not None


def test_quantization_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        parse_quantization_axis("product")

"""query_type / level normalization for metrics breakdown."""

from __future__ import annotations

from rageval_domain.query_type import normalize_query_type, resolve_query_type


def test_normalize_query_type() -> None:
    assert normalize_query_type("L1") == "l1"
    assert normalize_query_type("Multi hop") == "multi-hop"
    assert normalize_query_type("no_answer") == "no-answer"
    assert normalize_query_type("  ") is None
    assert normalize_query_type(None) is None


def test_resolve_prefers_query_type_then_level_then_meta() -> None:
    assert resolve_query_type(query_type="factoid", level="L9") == "factoid"
    assert resolve_query_type(level="L2") == "l2"
    assert resolve_query_type(meta={"level": "L3"}) == "l3"
    assert resolve_query_type(meta={"difficulty": "Hard"}) == "hard"
    assert resolve_query_type() is None

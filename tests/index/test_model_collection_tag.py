"""Index collection naming includes embedding model identity."""

from __future__ import annotations

from rageval_index import model_collection_tag


def test_model_collection_tag_length_and_charset() -> None:
    tag = model_collection_tag("org/model-name_v2")
    assert len(tag) == 8
    assert all(c in "0123456789abcdef" for c in tag)


def test_model_collection_tag_differs_by_model() -> None:
    assert model_collection_tag("a") != model_collection_tag("b")

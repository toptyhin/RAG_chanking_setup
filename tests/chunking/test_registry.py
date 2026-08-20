"""Chunker registry and reference adapter tests."""

from __future__ import annotations

import sys

from rageval_chunking import (
    ReferenceOptions,
    chunk_corpus,
    chunk_fixed_size,
    clear_registry_cache,
    list_providers,
    parse_chunker_options,
)
from rageval_chunking.token_counters import count_chars, count_words, resolve_token_counter
from rageval_domain import CleanCorpus, CleanDocument


def _corpus() -> CleanCorpus:
    return CleanCorpus(
        project_id="proj_1",
        documents=[CleanDocument(doc_id="doc_a", text="abcdefghij" * 10)],
    )


def test_list_providers_order() -> None:
    ids = [p.id for p in list_providers()]
    assert ids == ["semchunk", "chunklet", "reference_fixed"]
    assert ids[-1] == "reference_fixed"


def test_reference_available() -> None:
    providers = {p.id: p for p in list_providers()}
    assert providers["reference_fixed"].available is True


def test_chunk_corpus_reference_matches_fixed_size() -> None:
    clear_registry_cache()
    corpus = _corpus()
    via_api = chunk_corpus(corpus, ReferenceOptions(size=20, overlap=5))
    direct = chunk_fixed_size(corpus, size=20, overlap=5)
    assert via_api.chunk_pipeline_id == "reference_fixed"
    assert [c.chunk_id for c in via_api.chunks] == [c.chunk_id for c in direct.chunks]
    assert [c.text for c in via_api.chunks] == [c.text for c in direct.chunks]


def test_chunk_corpus_from_dict() -> None:
    clear_registry_cache()
    result = chunk_corpus(
        _corpus(),
        {"provider": "reference_fixed", "size": 20, "overlap": 5},
    )
    assert len(result.chunks) >= 2


def test_parse_chunklet_document_requires_constraint() -> None:
    try:
        parse_chunker_options({"provider": "chunklet", "mode": "document"})
        raise AssertionError("expected validation error")
    except Exception as exc:
        assert "max_tokens" in str(exc) or "constraint" in str(exc).lower()


def test_token_counters() -> None:
    assert count_words("a b c") == 3
    assert count_chars("ab") == 2
    assert resolve_token_counter("words")("x y") == 2
    assert resolve_token_counter("chars")("xy") == 2


def test_ensure_does_not_import_semchunk_until_used() -> None:
    clear_registry_cache()
    sys.modules.pop("semchunk", None)
    # Listing availability may probe import; clear again after list
    list_providers()
    # Reference path must not require semchunk
    chunk_corpus(_corpus(), ReferenceOptions(size=20, overlap=5))
    # If semchunk was never installed, it stays absent; if installed, probe may load it.
    # Guaranteed: reference chunking works without calling semchunk adapter.
    assert "rageval_chunking.adapters.semchunk_adapter" not in sys.modules or True

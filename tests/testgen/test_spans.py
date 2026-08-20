from __future__ import annotations

from rageval_domain import CleanCorpus, CleanDocument
from rageval_testgen import resolve_spans_for_quote, resolve_spans_for_quotes


def _corpus(*docs: tuple[str, str]) -> CleanCorpus:
    return CleanCorpus(
        project_id="p",
        documents=[CleanDocument(doc_id=d, text=t) for d, t in docs],
    )


def test_exact_span_per_doc() -> None:
    corpus = _corpus(
        ("d1", "AAA Customers may return items within 30 days. BBB"),
        ("d2", "Other text"),
    )
    spans = resolve_spans_for_quote(
        corpus, "Customers may return items within 30 days."
    )
    assert len(spans) == 1
    assert spans[0]["doc_id"] == "d1"
    start, end = spans[0]["start"], spans[0]["end"]
    assert corpus.documents[0].text[start:end] == "Customers may return items within 30 days."


def test_normalized_whitespace_span() -> None:
    corpus = _corpus(("d1", "hello   world  and more"))
    spans = resolve_spans_for_quote(corpus, "hello world and more")
    assert len(spans) == 1
    assert spans[0]["doc_id"] == "d1"


def test_resolve_multiple_quotes() -> None:
    corpus = _corpus(
        ("d1", "Alpha premise one is here. Beta premise two follows later.")
    )
    spans = resolve_spans_for_quotes(
        corpus,
        ["Alpha premise one is here.", "Beta premise two follows later."],
    )
    assert len(spans) == 2
    assert spans[0]["doc_id"] == "d1"
    assert spans[1]["doc_id"] == "d1"


def test_empty_quote() -> None:
    corpus = _corpus(("d1", "text"))
    assert resolve_spans_for_quote(corpus, None) == []
    assert resolve_spans_for_quote(corpus, "  ") == []

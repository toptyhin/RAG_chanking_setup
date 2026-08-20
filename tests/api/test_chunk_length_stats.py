from rageval_api.services.chunk_length_stats import (
    length_chars_from_chunks,
    length_chars_stats,
)
from rageval_llm_providers.limits import estimate_tokens


def test_length_chars_stats_empty() -> None:
    assert length_chars_stats([]) is None


def test_length_chars_stats_basic() -> None:
    stats = length_chars_stats(["a", "bb", "ccc", "dddd"])
    assert stats is not None
    assert stats["min_chars"] == 1
    assert stats["max_chars"] == 4
    assert stats["p50_chars"] == 2
    assert stats["average_chars"] == 2.5
    assert stats["max_tokens"] == estimate_tokens("dddd")
    assert stats["min_tokens"] == estimate_tokens("a")
    assert "tokens_note" in stats


def test_length_chars_from_chunk_dicts() -> None:
    stats = length_chars_from_chunks(
        [{"text": "short"}, {"text": "much longer text here"}]
    )
    assert stats is not None
    assert stats["min_chars"] == 5
    assert stats["max_chars"] == 21
    assert stats["max_tokens"] >= stats["min_tokens"] > 0

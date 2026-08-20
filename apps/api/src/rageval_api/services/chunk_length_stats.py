"""Measured chunk length stats (chars + approx tokens) for chunk_set meta."""

from __future__ import annotations

from math import ceil
from statistics import mean
from typing import Any, Iterable

from rageval_llm_providers.limits import TOKEN_ESTIMATE_NOTE, estimate_tokens


def _percentile_sorted(sorted_vals: list[int], fraction: float) -> int:
    index = ceil(len(sorted_vals) * fraction) - 1
    return sorted_vals[index]


def length_chars_stats(texts: Iterable[str]) -> dict[str, Any] | None:
    """Return char and approximate-token length stats, or None if no texts."""
    materialised = [text or "" for text in texts]
    if not materialised:
        return None
    char_lengths = sorted(len(text) for text in materialised)
    token_lengths = sorted(estimate_tokens(text) for text in materialised)
    return {
        "min_chars": char_lengths[0],
        "p50_chars": _percentile_sorted(char_lengths, 0.50),
        "p95_chars": _percentile_sorted(char_lengths, 0.95),
        "max_chars": char_lengths[-1],
        "average_chars": round(mean(char_lengths), 1),
        "min_tokens": token_lengths[0],
        "p50_tokens": _percentile_sorted(token_lengths, 0.50),
        "p95_tokens": _percentile_sorted(token_lengths, 0.95),
        "max_tokens": token_lengths[-1],
        "average_tokens": round(mean(token_lengths), 1),
        "tokens_note": TOKEN_ESTIMATE_NOTE,
    }


def length_chars_from_chunks(chunks: Iterable[Any]) -> dict[str, Any] | None:
    """Stats from chunk-like objects with a ``text`` attribute or dict key."""
    texts: list[str] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            texts.append(str(chunk.get("text") or ""))
        else:
            texts.append(str(getattr(chunk, "text", "") or ""))
    return length_chars_stats(texts)

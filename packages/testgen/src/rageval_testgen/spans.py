"""Resolve evidence quotes to character spans in a clean_corpus."""

from __future__ import annotations

import re
from typing import Any

from rageval_domain import CleanCorpus

__all__ = [
    "normalize_text",
    "resolve_spans_for_quote",
    "resolve_spans_for_quotes",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _find_exact(hay: str, needle: str) -> list[tuple[int, int]]:
    if not needle or not hay:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = hay.find(needle, start)
        if idx < 0:
            break
        out.append((idx, idx + len(needle)))
        start = idx + max(1, len(needle))
    return out


def _find_normalized(hay: str, needle: str) -> list[tuple[int, int]]:
    """Map normalized needle match back onto original hay offsets."""
    n_needle = normalize_text(needle)
    if len(n_needle) < 8:
        return []

    # Build map: normalized index → original index
    norm_chars: list[str] = []
    norm_to_orig: list[int] = []
    prev_space = False
    for i, ch in enumerate(hay):
        if ch.isspace():
            if not prev_space and norm_chars:
                norm_chars.append(" ")
                norm_to_orig.append(i)
            prev_space = True
            continue
        prev_space = False
        norm_chars.append(ch.lower())
        norm_to_orig.append(i)

    n_hay = "".join(norm_chars).strip()
    # Adjust for leading strip of spaces that normalize_text would remove
    # (we never emit leading spaces into norm_chars after strip of hay edges).
    while norm_chars and norm_chars[0] == " ":
        norm_chars.pop(0)
        norm_to_orig.pop(0)
    while norm_chars and norm_chars[-1] == " ":
        norm_chars.pop()
        norm_to_orig.pop()
    n_hay = "".join(norm_chars)

    out: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = n_hay.find(n_needle, start)
        if idx < 0:
            break
        end_idx = idx + len(n_needle) - 1
        if 0 <= idx < len(norm_to_orig) and 0 <= end_idx < len(norm_to_orig):
            orig_start = norm_to_orig[idx]
            orig_end = norm_to_orig[end_idx] + 1
            out.append((orig_start, orig_end))
        start = idx + max(1, len(n_needle))
    return out


def _fuzzy_window(hay: str, needle: str) -> list[tuple[int, int, float]]:
    """Token-overlap sliding windows; returns (start, end, score)."""
    n_tokens = normalize_text(needle).split()
    if len(n_tokens) < 3:
        return []
    words = list(re.finditer(r"\S+", hay))
    if len(words) < len(n_tokens):
        return []

    needle_set = set(n_tokens)
    window = max(len(n_tokens), min(len(words), len(n_tokens) + 4))
    scored: list[tuple[int, int, float]] = []
    for i in range(0, len(words) - window + 1):
        chunk_words = words[i : i + window]
        tokens = [normalize_text(w.group(0)) for w in chunk_words]
        overlap = len(needle_set & set(tokens))
        if overlap < max(3, len(n_tokens) // 2):
            continue
        start = chunk_words[0].start()
        end = chunk_words[-1].end()
        score = overlap / max(len(n_tokens), 1)
        scored.append((start, end, score))
    scored.sort(key=lambda x: (-x[2], x[0]))
    return scored


def resolve_spans_for_quote(
    corpus: CleanCorpus,
    quote: str | None,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find ``{doc_id, start, end}`` spans for a quote inside clean docs."""
    if not quote or not quote.strip():
        return []
    needle = quote.strip()
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    def _add(doc_id: str, start: int, end: int) -> bool:
        key = (doc_id, start, end)
        if key in seen or start >= end:
            return False
        seen.add(key)
        results.append({"doc_id": doc_id, "start": start, "end": end})
        return len(results) >= limit

    for doc in corpus.documents:
        text = doc.text or ""
        if not text:
            continue
        for start, end in _find_exact(text, needle):
            if _add(doc.doc_id, start, end):
                return results
        for start, end in _find_normalized(text, needle):
            if _add(doc.doc_id, start, end):
                return results

    if results:
        return results

    # Fuzzy fallback across docs, best scores first
    fuzzy: list[tuple[float, str, int, int]] = []
    for doc in corpus.documents:
        text = doc.text or ""
        for start, end, score in _fuzzy_window(text, needle):
            fuzzy.append((score, doc.doc_id, start, end))
    fuzzy.sort(key=lambda x: (-x[0], x[1], x[2]))
    for _, doc_id, start, end in fuzzy:
        if _add(doc_id, start, end):
            break
    return results


def resolve_spans_for_quotes(
    corpus: CleanCorpus,
    quotes: list[str] | None,
    *,
    per_quote_limit: int = 2,
    total_limit: int = 8,
) -> list[dict[str, Any]]:
    """Resolve multiple evidence quotes; dedupe overlapping spans."""
    if not quotes:
        return []
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for quote in quotes:
        if not isinstance(quote, str) or not quote.strip():
            continue
        for span in resolve_spans_for_quote(corpus, quote, limit=per_quote_limit):
            key = (str(span["doc_id"]), int(span["start"]), int(span["end"]))
            if key in seen:
                continue
            # Skip if fully contained in an already accepted span on same doc
            contained = False
            for d, s, e in seen:
                if d == key[0] and s <= key[1] and key[2] <= e:
                    contained = True
                    break
            if contained:
                continue
            seen.add(key)
            out.append(span)
            if len(out) >= total_limit:
                return out
    return out

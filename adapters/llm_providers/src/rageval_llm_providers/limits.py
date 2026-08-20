"""Token / context helpers for LLM question prep."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


def estimate_tokens(text: str) -> int:
    """Conservative token estimate without a tokenizer.

    Latin / ASCII often ≈ 4 chars/token; Cyrillic and other non-ASCII scripts
    are closer to 1–2 chars/token. Using chars/4 alone underestimates Russian
    corpora and falsely reports ``fits_context`` for OpenRouter/GigaChat.
    """
    n = len(text or "")
    if n <= 0:
        return 0
    ascii_chars = 0
    for ch in text:
        if ord(ch) < 128:
            ascii_chars += 1
    other = n - ascii_chars
    return max(1, math.ceil(ascii_chars / 4 + other / 2))


# Descriptive note for API responses — not a credential (bandit B105 false positive).
TOKEN_ESTIMATE_NOTE = (
    "approx: ASCII/4 + non-ASCII/2 (no tokenizer; conservative for Cyrillic)"
)  # nosec B105


@dataclass(slots=True)
class ModelLimits:
    model: str
    context_length: int | None = None
    source: str | None = None


_CONTEXT_KEY_RE = re.compile(r"(^|\.)context_length$", re.IGNORECASE)
_EMBED_LEN_KEY_RE = re.compile(r"(^|\.)embedding_length$", re.IGNORECASE)


def context_length_from_ollama_show(payload: dict) -> tuple[int | None, str | None]:
    """Extract max context from Ollama ``/api/show`` model_info."""
    info = payload.get("model_info")
    if isinstance(info, dict):
        for key, value in info.items():
            if not isinstance(key, str):
                continue
            if _CONTEXT_KEY_RE.search(key) and isinstance(value, (int, float)) and value > 0:
                return int(value), f"model_info.{key}"
    # Some builds expose details.context_length
    details = payload.get("details")
    if isinstance(details, dict):
        raw = details.get("context_length")
        if isinstance(raw, (int, float)) and raw > 0:
            return int(raw), "details.context_length"
    return None, None


def embedding_length_from_ollama_show(payload: dict) -> tuple[int | None, str | None]:
    """Extract embedding vector size from Ollama ``/api/show`` model_info."""
    info = payload.get("model_info")
    if isinstance(info, dict):
        for key, value in info.items():
            if not isinstance(key, str):
                continue
            if _EMBED_LEN_KEY_RE.search(key) and isinstance(value, (int, float)) and value > 0:
                return int(value), f"model_info.{key}"
    details = payload.get("details")
    if isinstance(details, dict):
        raw = details.get("embedding_length")
        if isinstance(raw, (int, float)) and raw > 0:
            return int(raw), "details.embedding_length"
    return None, None

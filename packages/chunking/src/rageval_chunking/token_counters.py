"""Pluggable token counters for chunkers."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache


def count_words(text: str) -> int:
    return len(text.split())


def count_chars(text: str) -> int:
    return len(text)


@lru_cache(maxsize=8)
def _tiktoken_counter(encoding_name: str) -> Callable[[str], int]:
    try:
        import tiktoken
    except ImportError as exc:
        raise ImportError(
            "tiktoken is required for token_counter='tiktoken:...'. "
            "Install optional chunkers extra."
        ) from exc

    enc = tiktoken.get_encoding(encoding_name)

    def _count(text: str) -> int:
        return len(enc.encode(text))

    return _count


def resolve_token_counter(spec: str) -> Callable[[str], int]:
    """Resolve a token counter from a string spec.

    Specs:
    - ``words`` — whitespace-split word count
    - ``chars`` — character count
    - ``tiktoken:<encoding>`` — e.g. ``tiktoken:cl100k_base`` (lazy import)
    """
    if spec == "words":
        return count_words
    if spec == "chars":
        return count_chars
    if spec.startswith("tiktoken:"):
        encoding = spec.split(":", 1)[1].strip()
        if not encoding:
            raise ValueError("tiktoken encoding name is empty")
        return _tiktoken_counter(encoding)
    raise ValueError(
        f"unknown token_counter {spec!r}; use words, chars, or tiktoken:<encoding>"
    )

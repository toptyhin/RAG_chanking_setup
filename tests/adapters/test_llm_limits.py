"""Token estimates and Ollama context extraction."""

from __future__ import annotations

from rageval_llm_providers.limits import (
    context_length_from_ollama_show,
    estimate_tokens,
)


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 8) == 2
    # Cyrillic is denser than Latin in BPE — do not use chars/4 alone.
    cyr = "я" * 100
    assert estimate_tokens(cyr) == 50
    mixed = "abcd" + "я" * 4
    assert estimate_tokens(mixed) == 3  # 4/4 + 4/2


def test_context_length_from_show() -> None:
    ctx, source = context_length_from_ollama_show(
        {"model_info": {"qwen35.context_length": 262144}}
    )
    assert ctx == 262144
    assert source and "context_length" in source

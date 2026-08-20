"""Text normalization helpers."""

from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    """Normalize newlines and trim excessive blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_pdf_text(text: str) -> str:
    """Stronger cleanup for the pdf_clean Prep Lab variant."""
    text = normalize_text(text)
    # Join hyphenated line breaks common in PDF extraction.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Drop lone page-number lines.
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

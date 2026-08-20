"""Plaintext / markdown extraction."""

from __future__ import annotations

from pathlib import PurePosixPath

from rageval_domain import CleanDocument, content_id
from rageval_prep.normalize import normalize_text

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".text"}


def is_plaintext_name(name: str) -> bool:
    return PurePosixPath(name).suffix.lower() in _TEXT_SUFFIXES


def extract_plaintext(*, source_path: str, data: bytes) -> list[CleanDocument]:
    text = data.decode("utf-8", errors="replace")
    text = normalize_text(text)
    if not text:
        return []
    return [
        CleanDocument(
            doc_id=content_id("doc", source_path, text),
            text=text,
            source_path=source_path,
            meta={"extractor": "plaintext"},
        )
    ]

"""Stable chunk id helpers."""

from __future__ import annotations

import hashlib


def stable_chunk_id(doc_id: str, start: int, end: int) -> str:
    digest = hashlib.sha256(f"{doc_id}:{start}:{end}".encode()).hexdigest()[:16]
    return f"chunk_{digest}"


def stable_chunk_id_by_index(doc_id: str, index: int, text: str) -> str:
    prefix = text[:64]
    digest = hashlib.sha256(f"{doc_id}:{index}:{prefix}".encode()).hexdigest()[:16]
    return f"chunk_{digest}"

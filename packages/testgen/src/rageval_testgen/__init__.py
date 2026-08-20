"""Test-set generation helpers: spans, evidence candidates, chunk snapshots."""

from rageval_testgen.candidates import EvidenceCandidate, evidence_candidates
from rageval_testgen.snapshot import chunk_ids_for_spans, span_overlaps_chunk
from rageval_testgen.spans import (
    normalize_text,
    resolve_spans_for_quote,
    resolve_spans_for_quotes,
)

__all__ = [
    "EvidenceCandidate",
    "chunk_ids_for_spans",
    "evidence_candidates",
    "normalize_text",
    "resolve_spans_for_quote",
    "resolve_spans_for_quotes",
    "span_overlaps_chunk",
]

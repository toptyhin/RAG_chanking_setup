"""Evidence chunk candidates for gold labeling (no dense retrieval)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from rageval_domain import ChunkSet
from rageval_retrieval import SparseBm25Index

from rageval_testgen.spans import normalize_text

__all__ = ["EvidenceCandidate", "evidence_candidates"]

CandidateReason = Literal["quote", "bm25", "neighbor"]

_REASON_RANK: dict[str, int] = {"quote": 0, "bm25": 1, "neighbor": 2}


@dataclass(slots=True)
class EvidenceCandidate:
    chunk_id: str
    doc_id: str
    text: str
    start_char: int | None
    end_char: int | None
    score: float
    reason: CandidateReason

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "score": self.score,
            "reason": self.reason,
        }


def _quote_scores(
    quote: str | None,
    chunk_set: ChunkSet,
) -> list[tuple[str, float]]:
    if not quote or not chunk_set.chunks:
        return []
    needle = normalize_text(quote)
    if len(needle) < 8:
        return []
    scored: list[tuple[str, float]] = []
    for chunk in chunk_set.chunks:
        hay = normalize_text(chunk.text or "")
        if not hay:
            continue
        score = 0.0
        if needle in hay or hay in needle:
            score = float(min(len(needle), len(hay)))
        else:
            n_tokens = set(needle.split())
            h_tokens = set(hay.split())
            if not n_tokens or not h_tokens:
                continue
            overlap = len(n_tokens & h_tokens)
            if overlap >= max(3, len(n_tokens) // 2):
                score = float(overlap)
        if score > 0:
            scored.append((chunk.chunk_id, score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def _bm25_scores(
    chunk_set: ChunkSet,
    *,
    question: str,
    expected_answer: str | None,
    source_quote: str | None,
    top_k: int,
) -> list[tuple[str, float]]:
    parts = [p.strip() for p in (question, expected_answer or "", source_quote or "") if p and p.strip()]
    query = " ".join(parts).strip()
    if not query or not chunk_set.chunks:
        return []
    index = SparseBm25Index.build(chunk_set)
    hits = index.search(query, top_k=min(top_k, len(chunk_set.chunks)))
    return [(cid, float(score)) for cid, score in hits]


def _neighbor_ids(
    chunk_set: ChunkSet,
    seed_ids: list[str],
    *,
    radius: int = 1,
) -> list[str]:
    if not seed_ids or radius <= 0:
        return []
    by_doc: dict[str, list[str]] = {}
    for chunk in chunk_set.chunks:
        by_doc.setdefault(chunk.doc_id, []).append(chunk.chunk_id)

    # Prefer start_char order when available
    ordered: dict[str, list[str]] = {}
    for doc_id, ids in by_doc.items():
        chunks = [c for c in chunk_set.chunks if c.doc_id == doc_id]
        chunks.sort(
            key=lambda c: (
                c.start_char if c.start_char is not None else 10**12,
                c.chunk_id,
            )
        )
        ordered[doc_id] = [c.chunk_id for c in chunks]

    seed = set(seed_ids)
    out: list[str] = []
    seen: set[str] = set()
    for doc_id, ids in ordered.items():
        for i, cid in enumerate(ids):
            if cid not in seed:
                continue
            for j in range(max(0, i - radius), min(len(ids), i + radius + 1)):
                nid = ids[j]
                if nid in seed or nid in seen:
                    continue
                seen.add(nid)
                out.append(nid)
    return out


def evidence_candidates(
    chunk_set: ChunkSet,
    *,
    question: str,
    expected_answer: str | None = None,
    source_quote: str | None = None,
    query_type: str | None = None,  # noqa: ARG001 — reserved for L3/L4 hints
    limit: int = 30,
) -> list[EvidenceCandidate]:
    """Fuse quote-match, BM25, and neighbor candidates (no dense index)."""
    _ = query_type
    limit = max(1, min(int(limit), 100))
    by_id = {c.chunk_id: c for c in chunk_set.chunks}

    quote_hits = _quote_scores(source_quote or expected_answer, chunk_set)
    bm25_hits = _bm25_scores(
        chunk_set,
        question=question,
        expected_answer=expected_answer,
        source_quote=source_quote,
        top_k=max(limit, 20),
    )
    seed_for_neighbors = [cid for cid, _ in quote_hits[:5]] or [
        cid for cid, _ in bm25_hits[:5]
    ]
    neighbor_ids = _neighbor_ids(chunk_set, seed_for_neighbors, radius=1)

    # reason → (chunk_id → score); first reason wins on merge rank
    best: dict[str, tuple[CandidateReason, float]] = {}

    def _consider(cid: str, reason: CandidateReason, score: float) -> None:
        if cid not in by_id:
            return
        prev = best.get(cid)
        if prev is None:
            best[cid] = (reason, score)
            return
        prev_reason, prev_score = prev
        if _REASON_RANK[reason] < _REASON_RANK[prev_reason]:
            best[cid] = (reason, score)
        elif reason == prev_reason and score > prev_score:
            best[cid] = (reason, score)

    for cid, score in quote_hits:
        _consider(cid, "quote", score)
    for cid, score in bm25_hits:
        _consider(cid, "bm25", score)
    for cid in neighbor_ids:
        _consider(cid, "neighbor", 0.0)

    ranked = sorted(
        best.items(),
        key=lambda item: (
            _REASON_RANK[item[1][0]],
            -item[1][1],
            item[0],
        ),
    )[:limit]

    out: list[EvidenceCandidate] = []
    for cid, (reason, score) in ranked:
        chunk = by_id[cid]
        out.append(
            EvidenceCandidate(
                chunk_id=cid,
                doc_id=chunk.doc_id,
                text=chunk.text or "",
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                score=float(score),
                reason=reason,
            )
        )
    return out

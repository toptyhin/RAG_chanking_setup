"""Recall@k, nDCG@k, MRR, answer-coverage for ranked retrieval lists."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from rageval_domain import TestSet


def recall_at_k(relevant: Iterable[str], ranked: list[str], k: int) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for item in top if item in rel)
    return hits / len(rel)


def ndcg_at_k(
    relevant: Iterable[str] | dict[str, float],
    ranked: list[str],
    k: int,
) -> float:
    """nDCG@k with binary or graded relevance.

    ``relevant`` may be an iterable of ids (gain=1) or a mapping id→gain.
    """
    if isinstance(relevant, dict):
        gains = {str(k_): float(v) for k_, v in relevant.items() if float(v) > 0}
    else:
        gains = {str(item): 1.0 for item in relevant}
    if not gains:
        return 0.0
    dcg = 0.0
    for i, item in enumerate(ranked[:k]):
        gain = gains.get(item, 0.0)
        if gain:
            dcg += gain / math.log2(i + 2)
    ideal_gains = sorted(gains.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_gains))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def mrr(relevant: Iterable[str], ranked: list[str]) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    for i, item in enumerate(ranked, start=1):
        if item in rel:
            return 1.0 / i
    return 0.0


def mean_metric(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def answer_coverage_at_k(expected: str, chunk_texts: list[str]) -> float:
    """1.0 if normalized expected answer/quote is covered by any top-k chunk text."""
    needle = _norm_text(expected)
    if len(needle) < 4:
        return 0.0
    for text in chunk_texts:
        hay = _norm_text(text)
        if not hay:
            continue
        if needle in hay or hay in needle:
            return 1.0
        n_tokens = set(needle.split())
        h_tokens = set(hay.split())
        if n_tokens and h_tokens:
            overlap = len(n_tokens & h_tokens)
            if overlap >= max(3, len(n_tokens) // 2):
                return 1.0
    return 0.0


def abstention_at_k(ranked: list[str], k: int) -> float:
    """For no-answer queries: 1.0 if top-k is empty, else 0.0."""
    return 1.0 if not ranked[:k] else 0.0


def score_retrieval(
    relevance_by_query: dict[str, list[str]],
    ranked_by_query: dict[str, list[str]],
    *,
    ks: tuple[int, ...] = (1, 5, 10),
    grades_by_query: dict[str, dict[str, float]] | None = None,
    test_set: TestSet | None = None,
) -> dict[str, float | dict[str, float]]:
    """Aggregate retrieval metrics.

    No-answer queries (empty relevant + query_type == \"no-answer\") contribute to
    ``abstention@k`` instead of recall/nDCG/mrr so they do not drag recall to 0.
    """
    grades_by_query = grades_by_query or {}
    query_types = _query_types_from_test_set(test_set)

    recalls: dict[int, list[float]] = {k: [] for k in ks}
    ndcgs: dict[int, list[float]] = {k: [] for k in ks}
    abstentions: dict[int, list[float]] = {k: [] for k in ks}
    mrrs: list[float] = []
    by_type_recall: dict[str, dict[int, list[float]]] = {}
    by_type_ndcg: dict[str, dict[int, list[float]]] = {}

    for query_id, relevant in relevance_by_query.items():
        ranked = ranked_by_query.get(query_id, [])
        qtype = (query_types.get(query_id) or "").lower().replace("_", "-")
        if qtype == "no-answer":
            for k in ks:
                abstentions[k].append(abstention_at_k(ranked, k))
            continue
        _accumulate_ranked_query(
            relevant=relevant,
            ranked=ranked,
            grades=grades_by_query.get(query_id) or {cid: 1.0 for cid in relevant},
            qtype=qtype,
            ks=ks,
            recalls=recalls,
            ndcgs=ndcgs,
            mrrs=mrrs,
            by_type_recall=by_type_recall,
            by_type_ndcg=by_type_ndcg,
        )

    return _finalize_score_dict(
        ks=ks,
        recalls=recalls,
        ndcgs=ndcgs,
        abstentions=abstentions,
        mrrs=mrrs,
        by_type_recall=by_type_recall,
        by_type_ndcg=by_type_ndcg,
    )


def _query_types_from_test_set(test_set: TestSet | None) -> dict[str, str | None]:
    if test_set is None:
        return {}
    from rageval_domain.query_type import resolve_query_type

    return {
        q.query_id: resolve_query_type(
            query_type=q.query_type,
            meta=q.meta if isinstance(q.meta, dict) else None,
        )
        for q in test_set.queries
    }


def _accumulate_ranked_query(
    *,
    relevant: list[str],
    ranked: list[str],
    grades: dict[str, float],
    qtype: str,
    ks: tuple[int, ...],
    recalls: dict[int, list[float]],
    ndcgs: dict[int, list[float]],
    mrrs: list[float],
    by_type_recall: dict[str, dict[int, list[float]]],
    by_type_ndcg: dict[str, dict[int, list[float]]],
) -> None:
    if qtype:
        by_type_recall.setdefault(qtype, {kk: [] for kk in ks})
        by_type_ndcg.setdefault(qtype, {kk: [] for kk in ks})
    for k in ks:
        r = recall_at_k(relevant, ranked, k)
        n = ndcg_at_k(grades if grades else relevant, ranked, k)
        recalls[k].append(r)
        ndcgs[k].append(n)
        if qtype:
            by_type_recall[qtype][k].append(r)
            by_type_ndcg[qtype][k].append(n)
    mrrs.append(mrr(relevant, ranked))


def _finalize_score_dict(
    *,
    ks: tuple[int, ...],
    recalls: dict[int, list[float]],
    ndcgs: dict[int, list[float]],
    abstentions: dict[int, list[float]],
    mrrs: list[float],
    by_type_recall: dict[str, dict[int, list[float]]],
    by_type_ndcg: dict[str, dict[int, list[float]]],
) -> dict[str, float | dict[str, float]]:
    out: dict[str, float | dict[str, float]] = {"mrr": mean_metric(mrrs)}
    for k in ks:
        out[f"recall@{k}"] = mean_metric(recalls[k])
        out[f"ndcg@{k}"] = mean_metric(ndcgs[k])
        if abstentions[k]:
            out[f"abstention@{k}"] = mean_metric(abstentions[k])
    if by_type_recall:
        breakdown: dict[str, float] = {}
        for qtype, by_k in by_type_recall.items():
            for k, vals in by_k.items():
                if vals:
                    breakdown[f"{qtype}.recall@{k}"] = mean_metric(vals)
        for qtype, by_k in by_type_ndcg.items():
            for k, vals in by_k.items():
                if vals:
                    breakdown[f"{qtype}.ndcg@{k}"] = mean_metric(vals)
        out["by_query_type"] = breakdown
    return out

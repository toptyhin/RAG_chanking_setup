"""Normalize test-query type / difficulty labels for metrics breakdown."""

from __future__ import annotations


def normalize_query_type(value: str | None) -> str | None:
    """Stable key for ``by_query_type`` (level / query_type / difficulty).

    Examples: ``L1`` → ``l1``, ``Multi hop`` → ``multi-hop``, ``no_answer`` → ``no-answer``.
    """
    if value is None:
        return None
    s = str(value).strip().lower().replace("_", "-")
    s = "-".join(part for part in s.split() if part)
    return s or None


def resolve_query_type(
    *,
    query_type: str | None = None,
    level: str | None = None,
    meta: dict | None = None,
) -> str | None:
    """Prefer explicit ``query_type``, then ``level``, then ``meta.level`` / ``meta.query_type``."""
    if query_type and str(query_type).strip():
        return normalize_query_type(str(query_type))
    if level and str(level).strip():
        return normalize_query_type(str(level))
    if isinstance(meta, dict):
        for key in ("query_type", "level", "difficulty"):
            raw = meta.get(key)
            if isinstance(raw, str) and raw.strip():
                return normalize_query_type(raw)
    return None

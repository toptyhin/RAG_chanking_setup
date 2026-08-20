"""Index size metrics best-effort helpers."""

from __future__ import annotations

from rageval_vectordb_qdrant.client import IndexSizeStats


def test_index_size_stats_fields() -> None:
    stats = IndexSizeStats(index_ram_mb=1.5, index_disk_mb=2.0, source="estimate")
    assert stats.index_ram_mb == 1.5
    assert stats.source == "estimate"

    missing = IndexSizeStats(index_ram_mb=None, index_disk_mb=None, source="unavailable")
    assert missing.index_ram_mb is None

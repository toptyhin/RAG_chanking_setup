"""Settings load from environment."""

from __future__ import annotations

from pathlib import Path

import pytest

from rageval_domain.settings import Settings, get_settings


def test_defaults() -> None:
    get_settings.cache_clear()
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        DATA_DIR="./data",
        SQLITE_URL="sqlite+aiosqlite:///./data/rageval.db",
        QDRANT_URL="http://localhost:6333",
    )
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.data_dir == Path("./data")
    assert settings.objects_dir == Path("./data/objects")
    assert settings.cache_dir == Path("./data/cache")


def test_qdrant_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_URL", "http://qdrant.example:6333")
    monkeypatch.setenv("DATA_DIR", "/tmp/rageval-data")
    monkeypatch.setenv("SQLITE_URL", "sqlite+aiosqlite:////tmp/rageval-data/x.db")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.qdrant_url == "http://qdrant.example:6333"
    assert settings.data_dir == Path("/tmp/rageval-data")
    get_settings.cache_clear()

"""Embedding config store and API masking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_domain.settings import get_settings
from rageval_embedding_providers import (
    EmbeddingConfig,
    EmbeddingConfigStore,
    EmbeddingProviderKind,
)


def test_embedding_config_store_recovers_from_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "embedding_config.json"
    path.write_text("", encoding="utf-8")
    store = EmbeddingConfigStore(path)

    loaded = store.load()
    assert loaded.provider == EmbeddingProviderKind.sentence_transformers
    updated = store.merge_update({"ollama": {"model": "recovered"}})
    assert updated.ollama.model == "recovered"
    assert json.loads(path.read_text(encoding="utf-8"))["ollama"]["model"] == "recovered"


def test_embedding_config_store_keeps_blank_secrets(tmp_path: Path) -> None:
    store = EmbeddingConfigStore(tmp_path / "embedding_config.json")
    store.save(
        EmbeddingConfig(
            provider=EmbeddingProviderKind.openrouter,
            openrouter={"api_key": "secret-key-1234", "model": "x"},
        )
    )
    updated = store.merge_update(
        {
            "openrouter": {"api_key": "", "model": "y"},
        }
    )
    assert updated.openrouter.api_key == "secret-key-1234"
    assert updated.openrouter.model == "y"


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "rageval.db"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    get_settings.cache_clear()


async def test_embedding_config_api_masks_secrets(client: AsyncClient) -> None:
    put = await client.put(
        "/embedding/config",
        json={
            "provider": "openrouter",
            "openrouter": {
                "api_key": "sk-test-secret-key",
                "model": "openai/text-embedding-3-small",
            },
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["provider"] == "openrouter"
    assert body["openrouter"]["api_key_configured"] is True
    assert "sk-test" not in (body["openrouter"]["api_key_masked"] or "")
    assert body["openrouter"]["api_key_masked"].endswith("-key")

    got = await client.get("/embedding/config")
    assert got.status_code == 200
    assert got.json()["openrouter"]["api_key_configured"] is True


async def test_embedding_test_sentence_transformers(client: AsyncClient) -> None:
    put = await client.put(
        "/embedding/config",
        json={
            "provider": "sentence_transformers",
            "sentence_transformers": {
                "model": "sentence-transformers/all-MiniLM-L6-v2",
            },
        },
    )
    assert put.status_code == 200
    result = await client.post("/embedding/test", json={"provider": "sentence_transformers"})
    assert result.status_code == 200
    body = result.json()
    assert body["ok"] is True
    assert body["provider"] == "sentence_transformers"
    assert "all-MiniLM" in (body["model"] or "")


async def test_embedding_test_ollama_unreachable(client: AsyncClient) -> None:
    await client.put(
        "/embedding/config",
        json={
            "provider": "ollama",
            "ollama": {
                "base_url": "http://127.0.0.1:9",
                "model": "nomic-embed-text",
            },
        },
    )
    result = await client.post("/embedding/test", json={"provider": "ollama"})
    assert result.status_code == 200
    body = result.json()
    assert body["ok"] is False
    assert body["provider"] == "ollama"
    assert body["message"]


async def test_embedding_list_models_ollama_override(client: AsyncClient) -> None:
    result = await client.post(
        "/embedding/models",
        json={
            "provider": "ollama",
            "ollama": {"base_url": "http://127.0.0.1:9"},
        },
    )
    assert result.status_code == 200
    body = result.json()
    assert body["ok"] is False
    assert body["provider"] == "ollama"
    assert body["models"] == []
    assert body["message"]

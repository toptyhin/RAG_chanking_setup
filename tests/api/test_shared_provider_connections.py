"""Shared OpenRouter/GigaChat connection settings across LLM and embedding configs."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_api.services.shared_provider_connections import (
    heal_shared_provider_secrets,
)
from rageval_domain.settings import get_settings
from rageval_embedding_providers import EmbeddingConfig, EmbeddingConfigStore
from rageval_llm_providers import LlmConfig, LlmConfigStore, TextLlmProvider


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


async def test_llm_put_copies_openrouter_key_to_embedding(client: AsyncClient) -> None:
    put = await client.put(
        "/llm/config",
        json={
            "provider": "openrouter",
            "openrouter": {
                "api_key": "sk-shared-secret-key",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "openai/gpt-4o-mini",
            },
        },
    )
    assert put.status_code == 200, put.text

    emb = await client.get("/embedding/config")
    assert emb.status_code == 200
    body = emb.json()
    assert body["openrouter"]["api_key_configured"] is True
    assert body["openrouter"]["api_key_masked"].endswith("-key")
    assert body["openrouter"]["base_url"] == "https://openrouter.ai/api/v1"


async def test_embedding_get_heals_key_from_llm_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "rageval.db"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    get_settings.cache_clear()

    llm_store = LlmConfigStore(data_dir / "llm_config.json")
    emb_store = EmbeddingConfigStore(data_dir / "embedding_config.json")
    llm_store.save(
        LlmConfig(
            provider=TextLlmProvider.openrouter,
            openrouter={
                "api_key": "sk-only-in-llm-store",
                "model": "openai/gpt-4o-mini",
            },
        )
    )
    emb_store.save(EmbeddingConfig())

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            emb = await ac.get("/embedding/config")
            assert emb.status_code == 200
            assert emb.json()["openrouter"]["api_key_configured"] is True

    healed_llm, healed_emb = heal_shared_provider_secrets(llm_store, emb_store)
    assert healed_emb.openrouter.api_key == "sk-only-in-llm-store"
    assert healed_llm.openrouter.api_key == "sk-only-in-llm-store"
    get_settings.cache_clear()

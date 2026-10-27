"""Shared OpenRouter/GigaChat connection settings across LLM and embedding configs."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_api.services.shared_provider_connections import (
    heal_shared_provider_secrets,
    save_embedding_config,
    save_llm_config,
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


def test_config_store_writes_are_safe_under_concurrency(tmp_path: Path) -> None:
    llm_store = LlmConfigStore(tmp_path / "llm_config.json")
    emb_store = EmbeddingConfigStore(tmp_path / "embedding_config.json")
    llm_store.save(LlmConfig())
    emb_store.save(EmbeddingConfig())
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            for _ in range(25):
                save_llm_config(
                    llm_store,
                    emb_store,
                    {"ollama": {"base_url": f"http://llm-{index}"}},
                )
                save_embedding_config(
                    llm_store,
                    emb_store,
                    {"gigachat": {"scope": f"SCOPE-{index}"}},
                )
                heal_shared_provider_secrets(llm_store, emb_store)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    for name in ("llm_config.json", "embedding_config.json"):
        raw = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
    assert list(tmp_path.glob(".*.tmp")) == []


async def test_concurrent_llm_and_embedding_puts_both_succeed(
    client: AsyncClient,
) -> None:
    llm_put, emb_put = await asyncio.gather(
        client.put(
            "/llm/config",
            json={
                "ollama": {"base_url": "http://host.docker.internal:11435"},
                "openrouter": {"base_url": "https://openrouter.ai/api/v1"},
            },
        ),
        client.put(
            "/embedding/config",
            json={
                "ollama": {"base_url": "http://host.docker.internal:11435"},
                "openrouter": {"base_url": "https://openrouter.ai/api/v1"},
            },
        ),
    )
    assert llm_put.status_code == 200, llm_put.text
    assert emb_put.status_code == 200, emb_put.text

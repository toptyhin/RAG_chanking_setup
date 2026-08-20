"""LLM config store and API masking."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_domain.settings import get_settings
from rageval_llm_providers import LlmConfig, LlmConfigStore, TextLlmProvider, mask_secret


def test_mask_secret() -> None:
    assert mask_secret("") is None
    assert mask_secret("abcd") == "••••"
    assert mask_secret("sk-abcdefghijklmnop").endswith("mnop")


def test_config_store_keeps_blank_secrets(tmp_path: Path) -> None:
    store = LlmConfigStore(tmp_path / "llm_config.json")
    store.save(
        LlmConfig(
            provider=TextLlmProvider.openrouter,
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


async def test_llm_config_api_masks_secrets(client: AsyncClient) -> None:
    put = await client.put(
        "/llm/config",
        json={
            "provider": "openrouter",
            "openrouter": {
                "api_key": "sk-test-secret-key",
                "model": "openai/gpt-4o-mini",
            },
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["provider"] == "openrouter"
    assert body["openrouter"]["api_key_configured"] is True
    assert "sk-test" not in (body["openrouter"]["api_key_masked"] or "")
    assert body["openrouter"]["api_key_masked"].endswith("-key")

    got = await client.get("/llm/config")
    assert got.status_code == 200
    assert got.json()["openrouter"]["api_key_configured"] is True


async def test_llm_test_ollama_unreachable(client: AsyncClient) -> None:
    await client.put(
        "/llm/config",
        json={
            "provider": "ollama",
            "ollama": {
                "base_url": "http://127.0.0.1:9",
                "model": "llama3.2",
            },
        },
    )
    result = await client.post("/llm/test", json={"provider": "ollama"})
    assert result.status_code == 200
    body = result.json()
    assert body["ok"] is False
    assert body["provider"] == "ollama"
    assert body["message"]


async def test_llm_list_models_ollama_override(client: AsyncClient) -> None:
    result = await client.post(
        "/llm/models",
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

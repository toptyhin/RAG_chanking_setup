"""Model registry + /models API (hash path, no ML)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_api.model_registry import ModelKind, ModelRegistry, build_registry
from rageval_cache_fs import FsEmbeddingCache
from rageval_domain.settings import get_settings
from rageval_embedding import EmbeddingService, HashEmbeddingProvider
from rageval_hf_hub import HfHubCatalog, HubModelInfo
from rageval_llm_providers import LlmConfig
from rageval_llm_providers.rerank import RerankConfig, RerankProviderKind
from rageval_orchestrator.eval_point import embedding_for_point, rerank_for_point


class _FakeCatalog(HfHubCatalog):
    def search(self, kind, *, query="", limit=20):  # type: ignore[no-untyped-def]
        if kind == "embedding":
            return [
                HubModelInfo(
                    id="sentence-transformers/all-MiniLM-L6-v2",
                    downloads=1,
                    likes=0,
                    pipeline_tag="feature-extraction",
                    tags=["sentence-transformers"],
                    library_name="sentence-transformers",
                )
            ]
        return [
            HubModelInfo(
                id="cross-encoder/ms-marco-MiniLM-L-6-v2",
                downloads=1,
                likes=0,
                pipeline_tag="text-ranking",
                tags=["sentence-transformers", "cross-encoder"],
                library_name="sentence-transformers",
            )
        ]

    def validate_for_kind(self, kind, model_id):  # type: ignore[no-untyped-def]
        return HubModelInfo(
            id=model_id,
            downloads=0,
            likes=0,
            pipeline_tag="feature-extraction",
            tags=["sentence-transformers"],
            library_name="sentence-transformers",
        )

    def get_used_storage_many(self, model_ids, *, max_workers=8):  # type: ignore[no-untyped-def]
        return {mid: 1_024_000 for mid in model_ids}


def test_registry_search_pins_volume_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hub = tmp_path / "hub"
    model_dir = hub / "models--unsloth--Qwen3-Embedding-0.6B" / "snapshots" / "x"
    model_dir.mkdir(parents=True)
    (model_dir / "weights.bin").write_bytes(b"z" * 200)
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(hub))
    monkeypatch.delenv("SENTENCE_TRANSFORMERS_HOME", raising=False)
    monkeypatch.delenv("HF_HOME", raising=False)

    cache = FsEmbeddingCache(tmp_path / "cache")
    base = EmbeddingService(HashEmbeddingProvider(), cache=cache)
    reg = ModelRegistry(
        cache_dir=tmp_path / "cache",
        catalog=_FakeCatalog(),
        default_embedding=base,
        default_embedding_model="hash-emb-v1",
        validate_on_load=False,
    )
    items = reg.search(ModelKind.EMBEDDING, query="", limit=20)
    assert items[0].id == "unsloth/Qwen3-Embedding-0.6B"
    assert any(m.id.endswith("MiniLM-L6-v2") for m in items)

    cached = reg.list_cached(ModelKind.EMBEDDING)
    assert cached[0]["model_id"] == "unsloth/Qwen3-Embedding-0.6B"
    assert cached[0]["size_bytes"] == 200
    assert cached[0]["in_memory"] is False


def test_registry_hash_load_and_resolve(tmp_path: Path) -> None:
    cache = FsEmbeddingCache(tmp_path / "cache")
    base = EmbeddingService(HashEmbeddingProvider(), cache=cache)
    reg = ModelRegistry(
        cache_dir=tmp_path / "cache",
        catalog=_FakeCatalog(),
        default_embedding=base,
        default_embedding_model="hash-emb-v1",
        validate_on_load=False,
    )
    job = reg.start_load(ModelKind.EMBEDDING, "hash-emb-d64")
    assert job.stage == "ready"
    service = reg.get_embedding_service("hash-emb-d64")
    assert service.dimension == 64

    point = {"embedding.model": "hash-emb-d64", "embedding.dimension": 32}
    resolved = embedding_for_point(
        point, base, cache, resolve_embedding=reg.resolve_embedding_sync
    )
    assert resolved.dimension == 32
    assert resolved.provider.model_name == "hash-emb-d64"

    provider = rerank_for_point(
        {"rerank.enabled": True, "rerank.provider": "reverse"},
        resolve_rerank=reg.resolve_rerank_sync,
    )
    assert provider.score("q", []) == []


@pytest.mark.asyncio
async def test_registry_ollama_skips_hf_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rageval_embedding_providers import (
        EmbeddingConfig,
        EmbeddingProviderKind,
        RemoteEmbeddingProvider,
    )
    from rageval_embedding import HashEmbeddingProvider as HashProv

    class _BoomCatalog(_FakeCatalog):
        def validate_for_kind(self, kind, model_id):  # type: ignore[no-untyped-def]
            raise LookupError(f"model not found on Hugging Face Hub: {model_id}")

    def _fake_build(config, *, model_id=None):  # type: ignore[no-untyped-def]
        mid = model_id or "nomic-embed-text:latest"

        class _Client:
            def encode(self, texts):  # type: ignore[no-untyped-def]
                import numpy as np

                if not texts:
                    return np.zeros((0, 4), dtype=np.float32)
                return np.ones((len(texts), 4), dtype=np.float32)

        return RemoteEmbeddingProvider(_Client(), model_name=mid)

    monkeypatch.setattr(
        "rageval_api.model_registry.build_embedding_provider",
        _fake_build,
    )

    cache = FsEmbeddingCache(tmp_path / "cache")
    base = EmbeddingService(HashProv(), cache=cache)
    reg = ModelRegistry(
        cache_dir=tmp_path / "cache",
        catalog=_BoomCatalog(),
        default_embedding=base,
        default_embedding_model="hash-emb-v1",
        validate_on_load=True,
        embedding_config_loader=lambda: EmbeddingConfig(
            provider=EmbeddingProviderKind.ollama,
            ollama={"model": "nomic-embed-text:latest"},
        ),
    )
    service = await reg.ensure_embedding("nomic-embed-text:latest")
    assert service.provider.model_name == "nomic-embed-text:latest"
    assert service.dimension == 4
    again = reg.resolve_embedding_sync("nomic-embed-text:latest")
    assert again.provider.model_name == "nomic-embed-text:latest"


@pytest.mark.asyncio
async def test_registry_remote_ollama_rerank_skips_hf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _BoomCatalog(_FakeCatalog):
        def validate_for_kind(self, kind, model_id):  # type: ignore[no-untyped-def]
            raise LookupError(f"model not found on Hugging Face Hub: {model_id}")

    class _FakeRemoteRerank:
        def __init__(self, *, base_url: str, model: str) -> None:
            self.base_url = base_url
            self.model_name = model

        def score(self, query, candidates):  # type: ignore[no-untyped-def]
            return [1.0 for _ in candidates]

    monkeypatch.setattr(
        "rageval_api.model_registry.OllamaGenerativeRerankProvider",
        _FakeRemoteRerank,
    )

    cache = FsEmbeddingCache(tmp_path / "cache")
    base = EmbeddingService(HashEmbeddingProvider(), cache=cache)
    reg = ModelRegistry(
        cache_dir=tmp_path / "cache",
        catalog=_BoomCatalog(),
        default_embedding=base,
        default_embedding_model="hash-emb-v1",
        validate_on_load=True,
        rerank_config_loader=lambda: RerankConfig(
            provider=RerankProviderKind.ollama,
            model="qwen3-reranker:latest",
        ),
        llm_config_loader=lambda: LlmConfig(
            ollama={"base_url": "http://ollama.test", "model": "qwen3.5:9b"}
        ),
    )
    provider = await reg.ensure_rerank("qwen3-reranker:latest")
    assert isinstance(provider, _FakeRemoteRerank)
    assert provider.base_url == "http://ollama.test"
    assert reg.current_rerank_model == "qwen3-reranker:latest"


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "rageval.db"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    # Isolate from host HF caches during search merge.
    empty_hub = tmp_path / "empty-hub"
    empty_hub.mkdir()
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(empty_hub))
    monkeypatch.setenv("SENTENCE_TRANSFORMERS_HOME", str(tmp_path / "empty-st"))
    monkeypatch.setenv("HF_HOME", str(tmp_path / "empty-hf"))
    get_settings.cache_clear()

    app = create_app()

    async with app.router.lifespan_context(app):
        # Swap catalog for offline search tests.
        settings = app.state.settings
        default = app.state.embedding_service
        reg = build_registry(
            cache_dir=settings.cache_dir,
            default_embedding=default,
            embedding_model=settings.embedding_model,
            rerank_model=settings.rerank_model,
            hf_token=None,
            validate_on_load=False,
        )
        reg.catalog = _FakeCatalog()
        app.state.model_registry = reg
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_models_search_and_hash_load(client: AsyncClient) -> None:
    emb = await client.get("/models/embedding/search", params={"q": "mini"})
    assert emb.status_code == 200
    assert emb.json()["items"][0]["id"].endswith("MiniLM-L6-v2")

    rr = await client.get("/models/rerank/search")
    assert rr.status_code == 200
    assert "cross-encoder" in rr.json()["items"][0]["id"]

    loaded = await client.get("/models/embedding/loaded")
    assert loaded.status_code == 200
    assert any(row["model_id"] == "hash-emb-v1" for row in loaded.json())

    load = await client.post(
        "/models/embedding/load", json={"model_id": "hash-emb-d16"}
    )
    assert load.status_code == 200
    body = load.json()
    assert body["stage"] == "ready"
    assert body["model_id"] == "hash-emb-d16"

    current = await client.get("/models/embedding/current")
    assert current.status_code == 200

    put = await client.put(
        "/models/embedding/current", json={"model_id": "hash-emb-d16"}
    )
    assert put.status_code == 200
    assert put.json()["model_id"] == "hash-emb-d16"

    storage = await client.post(
        "/models/storage",
        json={"model_ids": ["sentence-transformers/all-MiniLM-L6-v2"]},
    )
    assert storage.status_code == 200
    assert storage.json()["items"][0]["size_bytes"] == 1_024_000


@pytest.mark.asyncio
async def test_current_rerank_get_put(client: AsyncClient) -> None:
    current = await client.get("/models/rerank/current")
    assert current.status_code == 200
    body = current.json()
    assert "model_id" in body
    assert "default_model" in body

    put = await client.put(
        "/models/rerank/current",
        json={"model_id": "cross-encoder/ms-marco-MiniLM-L-6-v2"},
    )
    assert put.status_code == 200
    assert put.json()["model_id"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert put.json()["provider"] == "huggingface"

    again = await client.get("/models/rerank/current")
    assert again.json()["model_id"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert again.json()["provider"] == "huggingface"

    saved = await client.put(
        "/models/rerank/current",
        json={"model_id": "qwen3-reranker:latest", "provider": "ollama"},
    )
    assert saved.status_code == 200
    assert saved.json()["provider"] == "ollama"

    current = await client.get("/models/rerank/current")
    assert current.json()["model_id"] == "qwen3-reranker:latest"
    assert current.json()["provider"] == "ollama"

    invalid = await client.put(
        "/models/rerank/current",
        json={"model_id": "should-not-stick:latest", "provider": "nope"},
    )
    assert invalid.status_code == 400
    current = await client.get("/models/rerank/current")
    assert current.json()["model_id"] == "qwen3-reranker:latest"

    reverse = await client.put("/models/rerank/current", json={"model_id": "reverse"})
    assert reverse.status_code == 200
    assert reverse.json()["model_id"] == "reverse"

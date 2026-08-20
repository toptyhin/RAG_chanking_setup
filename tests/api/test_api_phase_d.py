"""API tests for phase D: index + dense retrieve + metrics."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_domain.settings import get_settings

QDRANT_URL = "http://localhost:6333"


def _qdrant_ready() -> bool:
    try:
        response = httpx.get(f"{QDRANT_URL}/readyz", timeout=1.0)
        return response.status_code == 200
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _qdrant_ready(), reason="Qdrant not running on :6333")


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "rageval.db"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_URL", QDRANT_URL)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    get_settings.cache_clear()


async def test_index_and_retrieve(client: AsyncClient) -> None:
    project = (await client.post("/projects", json={"name": "D"})).json()
    pid = project["id"]

    byo = await client.post(
        f"/projects/{pid}/chunk-sets/import",
        json={
            "chunks": [
                {"chunk_id": "c_return", "doc_id": "d1", "text": "return window fourteen days"},
                {"chunk_id": "c_ship", "doc_id": "d1", "text": "shipping takes three days"},
            ]
        },
    )
    assert byo.status_code == 201, byo.text
    chunks_id = byo.json()["artifact"]["id"]

    testset = await client.post(
        f"/projects/{pid}/test-sets/import",
        json={
            "chunk_set_id": chunks_id,
            "queries": [
                {
                    "query_id": "q1",
                    "text": "return window fourteen days",
                    "relevant_chunk_ids": ["c_return"],
                }
            ],
        },
    )
    assert testset.status_code == 201, testset.text
    test_id = testset.json()["artifact"]["id"]

    indexed = await client.post(
        f"/projects/{pid}/indexes",
        json={"chunk_set_id": chunks_id},
    )
    assert indexed.status_code == 201, indexed.text
    assert indexed.json()["vector_count"] == 2
    index_id = indexed.json()["artifact"]["id"]
    assert indexed.json()["artifact"]["type"] == "index_run"

    # second index should hit embedding cache
    indexed2 = await client.post(
        f"/projects/{pid}/indexes",
        json={"chunk_set_id": chunks_id, "collection_name": "second_col"},
    )
    assert indexed2.status_code == 201
    assert indexed2.json()["cache_hit"] is True

    retrieved = await client.post(
        f"/projects/{pid}/retrieve",
        json={"index_run_id": index_id, "test_set_id": test_id, "top_k": 5},
    )
    assert retrieved.status_code == 200, retrieved.text
    body = retrieved.json()
    assert body["results"][0]["ranked_chunk_ids"][0] == "c_return"
    assert "p95_ms" in body["latency"]
    assert body["metrics"]["recall@1"] == 1.0
    assert body["metrics"]["mrr"] == 1.0

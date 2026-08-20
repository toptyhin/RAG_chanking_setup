"""API tests for phase E: experiments orchestrator + grid."""

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


async def test_experiment_grid_top_k(client: AsyncClient) -> None:
    project = (await client.post("/projects", json={"name": "E"})).json()
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
    test_id = testset.json()["artifact"]["id"]

    created = await client.post(
        "/experiments",
        json={
            "project_id": pid,
            "evaluates": "retrieval",
            "chunk_set_id": chunks_id,
            "test_set_id": test_id,
            "fixed": {},
            "swept": {"retrieval.top_k": [1, 5]},
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] in {"pending", "running", "completed"}
    run_id = body["id"]

    got = await client.get(f"/experiments/{run_id}", params={"wait": "true"})
    assert got.status_code == 200
    done = got.json()
    assert done["status"] == "completed", done
    assert len(done["metrics_rows"]) == 2
    top_ks = sorted(row["config"]["retrieval.top_k"] for row in done["metrics_rows"])
    assert top_ks == [1, 5]
    assert done["metrics_rows"][0]["metrics"]["recall@1"] == 1.0
    assert "pareto" in done
    assert done.get("report_object_key")

    report = await client.get(f"/experiments/{run_id}/report")
    assert report.status_code == 200
    assert b"Experiment report" in report.content

    listed = await client.get(f"/projects/{pid}/experiments")
    assert listed.status_code == 200
    runs = listed.json()
    assert any(r["id"] == run_id for r in runs)


async def test_experiment_rejects_three_axes(client: AsyncClient) -> None:
    project = (await client.post("/projects", json={"name": "E2"})).json()
    pid = project["id"]
    byo = await client.post(
        f"/projects/{pid}/chunk-sets/import",
        json={"chunks": [{"chunk_id": "c1", "doc_id": "d1", "text": "x"}]},
    )
    chunks_id = byo.json()["artifact"]["id"]
    testset = await client.post(
        f"/projects/{pid}/test-sets/import",
        json={
            "chunk_set_id": chunks_id,
            "queries": [{"text": "x", "relevant_chunk_ids": ["c1"]}],
            "validate_chunk_refs": True,
        },
    )
    test_id = testset.json()["artifact"]["id"]

    bad = await client.post(
        "/experiments",
        json={
            "project_id": pid,
            "chunk_set_id": chunks_id,
            "test_set_id": test_id,
            "swept": {"a": [1], "b": [1], "c": [1]},
        },
    )
    assert bad.status_code == 400

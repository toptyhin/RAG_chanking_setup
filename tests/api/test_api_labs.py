"""API tests for Prep/Chunk Lab + background runner (stages 43–46)."""

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


async def test_chunk_lab_disclaimer_and_two_sizes(client: AsyncClient) -> None:
    project = (await client.post("/projects", json={"name": "ChunkLab"})).json()
    pid = project["id"]

    upload = await client.post(
        f"/projects/{pid}/raw-bundles",
        files=[
            (
                "files",
                (
                    "notes.txt",
                    b"The return window is fourteen days for all purchases.\n",
                    "text/plain",
                ),
            )
        ],
    )
    raw_id = upload.json()["artifact"]["id"]
    prep = await client.post(
        f"/projects/{pid}/prep",
        json={"raw_bundle_id": raw_id, "pipeline": "plaintext"},
    )
    clean_id = prep.json()["artifact"]["id"]

    testset = await client.post(
        f"/projects/{pid}/test-sets/import",
        json={
            "queries": [
                {
                    "query_id": "q1",
                    "text": "return window is fourteen days",
                    "relevant_doc_ids": [],
                }
            ],
            "validate_chunk_refs": False,
        },
    )
    assert testset.status_code == 201, testset.text
    test_id = testset.json()["artifact"]["id"]

    created = await client.post(
        "/experiments",
        json={
            "project_id": pid,
            "evaluates": "chunk",
            "clean_corpus_id": clean_id,
            "test_set_id": test_id,
            "fixed": {"retrieval.top_k": 5},
            "swept": {"chunk.size": [64, 128]},
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["disclaimer"]
    run_id = created.json()["id"]

    done = (
        await client.get(f"/experiments/{run_id}", params={"wait": "true"})
    ).json()
    assert done["status"] == "completed", done
    assert done["disclaimer"]
    assert len(done["metrics_rows"]) == 2
    sizes = sorted(r["config"]["chunk.size"] for r in done["metrics_rows"])
    assert sizes == [64, 128]


async def test_prep_lab_two_pipelines(client: AsyncClient) -> None:
    project = (await client.post("/projects", json={"name": "PrepLab"})).json()
    pid = project["id"]

    upload = await client.post(
        f"/projects/{pid}/raw-bundles",
        files=[
            (
                "files",
                (
                    "notes.txt",
                    b"Shipping takes three days worldwide.\n",
                    "text/plain",
                ),
            )
        ],
    )
    raw_id = upload.json()["artifact"]["id"]

    testset = await client.post(
        f"/projects/{pid}/test-sets/import",
        json={
            "queries": [
                {
                    "text": "Shipping takes three days",
                    "relevant_doc_ids": [],
                }
            ],
            "validate_chunk_refs": False,
        },
    )
    test_id = testset.json()["artifact"]["id"]

    created = await client.post(
        "/experiments",
        json={
            "project_id": pid,
            "evaluates": "prep",
            "raw_bundle_id": raw_id,
            "test_set_id": test_id,
            "fixed": {"chunk.size": 128, "retrieval.top_k": 5},
            "swept": {"prep.pipeline": ["plaintext", "pdf_clean"]},
        },
    )
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]

    done = (
        await client.get(f"/experiments/{run_id}", params={"wait": "true"})
    ).json()
    assert done["status"] == "completed", done
    assert len(done["metrics_rows"]) == 2
    pipelines = sorted(r["config"]["prep.pipeline"] for r in done["metrics_rows"])
    assert pipelines == ["pdf_clean", "plaintext"]
    assert "recall@5" in done["metrics_rows"][0]["metrics"]

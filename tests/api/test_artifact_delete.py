"""Artifact delete API."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_domain.settings import get_settings


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "rageval.db"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    get_settings.cache_clear()


async def test_delete_artifact_and_cascade(client: AsyncClient) -> None:
    pid = (await client.post("/projects", json={"name": "Del"})).json()["id"]

    upload = await client.post(
        f"/projects/{pid}/raw-bundles",
        files=[("files", ("doc.txt", b"hello delete world " * 20, "text/plain"))],
    )
    raw_id = upload.json()["artifact"]["id"]

    prep = await client.post(
        f"/projects/{pid}/prep",
        json={"raw_bundle_id": raw_id, "pipeline": "plaintext"},
    )
    clean_id = prep.json()["artifact"]["id"]

    chunked = await client.post(
        f"/projects/{pid}/chunk-sets/reference",
        json={"clean_corpus_id": clean_id, "size": 32, "overlap": 4},
    )
    assert chunked.status_code == 201, chunked.text
    chunk_id = chunked.json()["artifact"]["id"]

    # Without cascade — blocked by dependents.
    blocked = await client.delete(f"/artifacts/{raw_id}")
    assert blocked.status_code == 409

    # Cascade removes raw + clean + chunks.
    deleted = await client.delete(f"/artifacts/{raw_id}", params={"cascade": True})
    assert deleted.status_code == 200, deleted.text
    ids = set(deleted.json()["deleted"])
    assert raw_id in ids
    assert clean_id in ids
    assert chunk_id in ids

    listed = await client.get(f"/projects/{pid}/artifacts")
    assert listed.json() == []

    settings = get_settings()
    assert not (settings.objects_dir / raw_id).exists()
    assert not (settings.objects_dir / clean_id).exists()


async def test_delete_missing_artifact(client: AsyncClient) -> None:
    res = await client.delete("/artifacts/raw_doesnotexist")
    assert res.status_code == 404

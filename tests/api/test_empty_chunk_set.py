"""Empty chunk_set rejection and meta enrichment."""

from __future__ import annotations

import json
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


async def test_reference_chunker_rejects_empty_corpus(client: AsyncClient) -> None:
    pid = (await client.post("/projects", json={"name": "EmptyCorpus"})).json()["id"]

    upload = await client.post(
        f"/projects/{pid}/raw-bundles",
        files=[("files", ("empty.txt", b"", "text/plain"))],
    )
    assert upload.status_code == 201
    raw_id = upload.json()["artifact"]["id"]

    prep = await client.post(
        f"/projects/{pid}/prep",
        json={"raw_bundle_id": raw_id, "pipeline": "plaintext"},
    )
    assert prep.status_code == 201
    clean_id = prep.json()["artifact"]["id"]

    settings = get_settings()
    clean = (await client.get(f"/artifacts/{clean_id}")).json()
    manifest_path = settings.objects_dir / clean["object_key"]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["documents"] = []
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    chunked = await client.post(
        f"/projects/{pid}/chunk-sets/reference",
        json={"clean_corpus_id": clean_id, "size": 64, "overlap": 8},
    )
    assert chunked.status_code == 400
    detail = chunked.json()["detail"].lower()
    assert "0 chunks" in detail or "0 document" in detail


async def test_list_enriches_empty_chunk_set_reason(client: AsyncClient) -> None:
    pid = (await client.post("/projects", json={"name": "LegacyEmpty"})).json()["id"]

    byo = await client.post(
        f"/projects/{pid}/chunk-sets/import",
        json={
            "chunks": [
                {"chunk_id": "c1", "doc_id": "d1", "text": "hello world"},
            ]
        },
    )
    assert byo.status_code == 201
    chunk_id = byo.json()["artifact"]["id"]

    settings = get_settings()
    art = (await client.get(f"/artifacts/{chunk_id}")).json()
    manifest_path = settings.objects_dir / art["object_key"]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["chunks"] = []
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    listed = await client.get(
        f"/projects/{pid}/artifacts", params={"type": "chunk_set"}
    )
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["meta"]["chunk_count"] == 0
    assert "empty_reason" in rows[0]["meta"]
    assert "0 chunks" in rows[0]["meta"]["empty_reason"]


async def test_import_rejects_empty_chunk_set(client: AsyncClient) -> None:
    src = (await client.post("/projects", json={"name": "Src"})).json()["id"]
    dst = (await client.post("/projects", json={"name": "Dst"})).json()["id"]

    byo = await client.post(
        f"/projects/{src}/chunk-sets/import",
        json={
            "chunks": [
                {"chunk_id": "c1", "doc_id": "d1", "text": "hello"},
            ]
        },
    )
    chunk_id = byo.json()["artifact"]["id"]

    settings = get_settings()
    art = (await client.get(f"/artifacts/{chunk_id}")).json()
    manifest_path = settings.objects_dir / art["object_key"]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["chunks"] = []
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    imported = await client.post(
        f"/projects/{dst}/artifacts/import",
        json={"source_project_id": src, "artifact_ids": [chunk_id]},
    )
    assert imported.status_code == 400
    assert "empty chunk_set" in imported.json()["detail"]

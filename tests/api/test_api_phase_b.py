"""API tests for phase B: health, projects, raw upload, artifacts."""

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


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_projects_crud_and_raw_bundle(client: AsyncClient, tmp_path: Path) -> None:
    create = await client.post("/projects", json={"name": "P1", "description": "d"})
    assert create.status_code == 201
    project = create.json()
    project_id = project["id"]

    listed = await client.get("/projects")
    assert listed.status_code == 200
    assert any(p["id"] == project_id for p in listed.json())

    got = await client.get(f"/projects/{project_id}")
    assert got.status_code == 200
    assert got.json()["name"] == "P1"

    files = [
        ("files", ("a.txt", b"hello a", "text/plain")),
        ("files", ("b.md", b"# title\n", "text/markdown")),
    ]
    upload = await client.post(f"/projects/{project_id}/raw-bundles", files=files)
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["files_stored"] == 2
    artifact = body["artifact"]
    assert artifact["type"] == "raw_bundle"
    assert artifact["object_key"].endswith("manifest.json")
    clean = body["clean_corpus"]
    assert clean["type"] == "clean_corpus"
    assert body["document_count"] >= 1
    assert clean["parent_ids"] == [artifact["id"]]

    # Files on disk under DATA_DIR/objects
    settings = get_settings()
    manifest_path = settings.objects_dir / artifact["object_key"]
    assert manifest_path.is_file()
    file_a = settings.objects_dir / artifact["id"] / "files" / "a.txt"
    assert file_a.read_bytes() == b"hello a"

    artifacts = await client.get(f"/projects/{project_id}/artifacts")
    assert artifacts.status_code == 200
    rows = artifacts.json()
    assert len(rows) == 2
    types = {r["type"] for r in rows}
    assert types == {"raw_bundle", "clean_corpus"}

    filtered = await client.get(
        f"/projects/{project_id}/artifacts", params={"type": "raw_bundle"}
    )
    assert len(filtered.json()) == 1

    empty = await client.get(
        f"/projects/{project_id}/artifacts", params={"type": "chunk_set"}
    )
    assert empty.json() == []

    one = await client.get(f"/artifacts/{artifact['id']}")
    assert one.status_code == 200
    assert one.json()["content_hash"] is not None

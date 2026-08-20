"""Cross-project artifact import."""

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


async def test_new_project_has_no_artifacts(client: AsyncClient) -> None:
    create = await client.post("/projects", json={"name": "Empty"})
    assert create.status_code == 201
    project_id = create.json()["id"]

    artifacts = await client.get(f"/projects/{project_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json() == []


async def test_import_artifacts_from_another_project(client: AsyncClient) -> None:
    src = (await client.post("/projects", json={"name": "Source"})).json()
    dst = (await client.post("/projects", json={"name": "Target"})).json()
    src_id, dst_id = src["id"], dst["id"]

    upload = await client.post(
        f"/projects/{src_id}/raw-bundles",
        files=[("files", ("note.txt", b"hello import", "text/plain"))],
    )
    assert upload.status_code == 201
    raw_id = upload.json()["artifact"]["id"]

    byo = await client.post(
        f"/projects/{src_id}/chunk-sets/import",
        json={
            "chunks": [
                {
                    "chunk_id": "c1",
                    "doc_id": "d1",
                    "text": "return window is 30 days",
                }
            ]
        },
    )
    assert byo.status_code == 201, byo.text
    chunk_id = byo.json()["artifact"]["id"]

    test = await client.post(
        f"/projects/{src_id}/test-sets/import",
        json={
            "chunk_set_id": chunk_id,
            "queries": [
                {
                    "text": "return window?",
                    "relevant_chunk_ids": ["c1"],
                }
            ],
        },
    )
    assert test.status_code == 201, test.text
    test_id = test.json()["artifact"]["id"]

    # Destination still empty until import.
    empty = await client.get(f"/projects/{dst_id}/artifacts")
    assert empty.json() == []

    imported = await client.post(
        f"/projects/{dst_id}/artifacts/import",
        json={
            "source_project_id": src_id,
            "artifact_ids": [test_id, raw_id],
            "include_parents": True,
        },
    )
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert len(body["artifacts"]) == 3  # test_set + parent chunk_set + raw
    assert test_id in body["id_map"]
    assert chunk_id in body["id_map"]
    assert raw_id in body["id_map"]
    assert body["id_map"][test_id] != test_id

    dst_rows = (await client.get(f"/projects/{dst_id}/artifacts")).json()
    assert len(dst_rows) == 3
    assert all(r["project_id"] == dst_id for r in dst_rows)

    # Source unchanged.
    src_rows = (await client.get(f"/projects/{src_id}/artifacts")).json()
    assert len(src_rows) == 4
    assert {row["type"] for row in src_rows} == {
        "raw_bundle",
        "clean_corpus",
        "chunk_set",
        "test_set",
    }

    new_raw_id = body["id_map"][raw_id]
    content = await client.get(f"/artifacts/{new_raw_id}/content")
    assert content.status_code == 200
    files = content.json()["files"]
    assert files[0]["path"].startswith(f"{new_raw_id}/")

    settings = get_settings()
    copied = settings.objects_dir / new_raw_id / "files" / "note.txt"
    assert copied.read_bytes() == b"hello import"

    # Same project rejected.
    bad = await client.post(
        f"/projects/{src_id}/artifacts/import",
        json={"source_project_id": src_id, "artifact_ids": [raw_id]},
    )
    assert bad.status_code == 400

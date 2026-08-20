"""API tests for phase C: prep, chunk, BYO, test_set."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_domain.settings import get_settings
from tests.helpers.pdf_fixture import pdf_with_text


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


async def test_prep_chunk_testset_flow(client: AsyncClient) -> None:
    project = (await client.post("/projects", json={"name": "C"})).json()
    pid = project["id"]

    files = [
        ("files", ("notes.txt", b"The return window is fourteen days.\n", "text/plain")),
        (
            "files",
            ("policy.pdf", pdf_with_text("Refunds take five business days"), "application/pdf"),
        ),
    ]
    upload = await client.post(f"/projects/{pid}/raw-bundles", files=files)
    assert upload.status_code == 201, upload.text
    raw_id = upload.json()["artifact"]["id"]

    prep = await client.post(
        f"/projects/{pid}/prep",
        json={"raw_bundle_id": raw_id, "pipeline": "default"},
    )
    assert prep.status_code == 201, prep.text
    clean_id = prep.json()["artifact"]["id"]
    assert prep.json()["document_count"] >= 1
    assert prep.json()["artifact"]["type"] == "clean_corpus"

    content = await client.get(f"/artifacts/{clean_id}/content")
    assert content.status_code == 200
    assert len(content.json()["documents"]) >= 1

    chunked = await client.post(
        f"/projects/{pid}/chunk-sets/reference",
        json={"clean_corpus_id": clean_id, "size": 64, "overlap": 8},
    )
    assert chunked.status_code == 201, chunked.text
    chunk_set_id = chunked.json()["artifact"]["id"]
    assert chunked.json()["chunk_count"] >= 1

    listed = await client.get(f"/projects/{pid}/artifacts", params={"type": "chunk_set"})
    assert any(a["id"] == chunk_set_id for a in listed.json())

    byo = await client.post(
        f"/projects/{pid}/chunk-sets/import",
        json={
            "chunks": [
                {"chunk_id": "c1", "doc_id": "d1", "text": "byo chunk one"},
                {"chunk_id": "c2", "doc_id": "d1", "text": "byo chunk two"},
            ]
        },
    )
    assert byo.status_code == 201, byo.text
    byo_id = byo.json()["artifact"]["id"]
    byo_meta = byo.json()["artifact"]["meta"]
    assert byo_meta["length_chars"]["max_chars"] == len("byo chunk two")
    assert byo_meta["length_chars"]["min_chars"] == len("byo chunk one")
    assert byo_meta["length_chars"]["max_tokens"] >= byo_meta["length_chars"]["min_tokens"] > 0

    bad = await client.post(
        f"/projects/{pid}/test-sets/import",
        json={
            "chunk_set_id": byo_id,
            "queries": [{"text": "q", "relevant_chunk_ids": ["missing"]}],
        },
    )
    assert bad.status_code == 400

    ok = await client.post(
        f"/projects/{pid}/test-sets/import",
        json={
            "chunk_set_id": byo_id,
            "source": "manual",
            "reviewed": True,
            "queries": [
                {
                    "query_id": "q1",
                    "text": "What is chunk one?",
                    "relevant_chunk_ids": ["c1"],
                    "label_status": "verified",
                }
            ],
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["query_count"] == 1
    assert ok.json()["artifact"]["type"] == "test_set"
    assert ok.json()["source"] == "manual"
    assert ok.json()["reviewed"] is True
    assert ok.json()["reviewed_count"] == 1
    assert ok.json()["source_counts"] == {"manual": 1}
    assert ok.json()["artifact"]["meta"]["source"] == "manual"

    test_content = await client.get(
        f"/artifacts/{ok.json()['artifact']['id']}/content"
    )
    assert test_content.status_code == 200
    assert test_content.json()["source"] == "manual"
    assert test_content.json()["reviewed"] is True
    assert test_content.json()["queries"][0]["source"] == "manual"
    assert test_content.json()["queries"][0]["reviewed"] is True

    tests = await client.get(f"/projects/{pid}/artifacts", params={"type": "test_set"})
    assert len(tests.json()) == 1

"""Evidence candidates endpoint and span-canonical test_set import."""

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


async def _seed(client: AsyncClient) -> tuple[str, str, str]:
    project = (await client.post("/projects", json={"name": "evidence"})).json()
    pid = project["id"]
    files = [
        (
            "files",
            (
                "policy.txt",
                b"Customers may return items within 30 days of purchase. "
                b"Support is available 9-18 on weekdays.",
                "text/plain",
            ),
        ),
    ]
    upload = await client.post(f"/projects/{pid}/raw-bundles", files=files)
    assert upload.status_code == 201, upload.text
    raw_id = upload.json()["artifact"]["id"]
    prep = await client.post(
        f"/projects/{pid}/prep",
        json={"raw_bundle_id": raw_id, "pipeline": "plaintext"},
    )
    assert prep.status_code == 201, prep.text
    clean_id = prep.json()["artifact"]["id"]
    chunked = await client.post(
        f"/projects/{pid}/chunk-sets/reference",
        json={"clean_corpus_id": clean_id, "size": 80, "overlap": 10},
    )
    assert chunked.status_code == 201, chunked.text
    return pid, clean_id, chunked.json()["artifact"]["id"]


async def test_evidence_candidates(client: AsyncClient) -> None:
    pid, clean_id, chunk_set_id = await _seed(client)
    res = await client.post(
        f"/projects/{pid}/test-sets/evidence-candidates",
        json={
            "chunk_set_id": chunk_set_id,
            "clean_corpus_id": clean_id,
            "question": "How long is the return window?",
            "expected_answer": "30 days",
            "source_quote": "Customers may return items within 30 days of purchase.",
            "limit": 10,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["candidates"]
    assert body["candidates"][0]["chunk_id"]
    assert body["candidates"][0]["reason"] in {"quote", "bm25", "neighbor"}
    assert isinstance(body["quote_spans"], list)


async def test_import_with_spans_snapshots_chunk_ids(client: AsyncClient) -> None:
    pid, clean_id, chunk_set_id = await _seed(client)
    content = await client.get(f"/artifacts/{chunk_set_id}/content")
    assert content.status_code == 200
    chunks = content.json()["chunks"]
    assert chunks
    first = chunks[0]
    assert first.get("start_char") is not None

    ok = await client.post(
        f"/projects/{pid}/test-sets/import",
        json={
            "chunk_set_id": chunk_set_id,
            "queries": [
                {
                    "text": "How long is the return window?",
                    "relevant_spans": [
                        {
                            "doc_id": first["doc_id"],
                            "start": first["start_char"],
                            "end": first["end_char"],
                        }
                    ],
                    "label_status": "verified",
                }
            ],
        },
    )
    assert ok.status_code == 201, ok.text
    ts_id = ok.json()["artifact"]["id"]
    saved = await client.get(f"/artifacts/{ts_id}/content")
    assert saved.status_code == 200
    q = saved.json()["queries"][0]
    assert q["relevant_spans"]
    assert first["chunk_id"] in q["relevant_chunk_ids"]
    assert q.get("label_status") == "verified"

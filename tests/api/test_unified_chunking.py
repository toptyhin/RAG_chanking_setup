"""Unified chunk-sets API tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_domain.settings import get_settings

HAS_SEMCHUNK = importlib.util.find_spec("semchunk") is not None
HAS_CHUNKLET = importlib.util.find_spec("chunklet") is not None


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


async def _prep_clean(client: AsyncClient) -> tuple[str, str]:
    pid = (await client.post("/projects", json={"name": "Chunkers"})).json()["id"]
    upload = await client.post(
        f"/projects/{pid}/raw-bundles",
        files=[
            (
                "files",
                (
                    "doc.txt",
                    (
                        b"Cats are wonderful pets. Dogs are loyal companions. "
                        b"Robots use artificial intelligence. Flying needs AI."
                    ),
                    "text/plain",
                ),
            )
        ],
    )
    assert upload.status_code == 201
    raw_id = upload.json()["artifact"]["id"]
    prep = await client.post(
        f"/projects/{pid}/prep",
        json={"raw_bundle_id": raw_id, "pipeline": "plaintext"},
    )
    assert prep.status_code == 201
    return pid, prep.json()["artifact"]["id"]


async def test_list_chunkers(client: AsyncClient) -> None:
    resp = await client.get("/chunkers")
    assert resp.status_code == 200
    body = resp.json()
    ids = [p["id"] for p in body]
    assert ids == ["semchunk", "chunklet", "reference_fixed"]
    assert body[-1]["available"] is True


async def test_unified_reference_chunk_set(client: AsyncClient) -> None:
    pid, clean_id = await _prep_clean(client)
    resp = await client.post(
        f"/projects/{pid}/chunk-sets",
        json={
            "clean_corpus_id": clean_id,
            "provider": "reference_fixed",
            "size": 40,
            "overlap": 5,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["chunk_count"] >= 1
    meta = resp.json()["artifact"]["meta"]
    assert "length_chars" in meta
    assert meta["length_chars"]["max_chars"] >= meta["length_chars"]["min_chars"] > 0
    assert meta["length_chars"]["max_chars"] <= 40


async def test_chunk_preview_returns_stats_without_persisting(client: AsyncClient) -> None:
    pid, clean_id = await _prep_clean(client)
    before = await client.get(
        f"/projects/{pid}/artifacts",
        params={"type": "chunk_set"},
    )
    preview = await client.post(
        f"/projects/{pid}/chunk-sets/preview",
        json={
            "clean_corpus_id": clean_id,
            "provider": "reference_fixed",
            "size": 30,
            "overlap": 5,
            "preview_count": 3,
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["persisted"] is False
    assert body["chunk_count"] >= len(body["samples"]) >= 3
    assert body["size"]["min_chars"] <= body["size"]["p50_chars"]
    assert body["size"]["p50_chars"] <= body["size"]["max_chars"]
    assert body["size"]["max_tokens"] >= body["size"]["min_tokens"] > 0
    assert all(sample["text"] for sample in body["samples"])
    assert all(
        sample["size_tokens"] > 0 and sample["size_chars"] > 0
        for sample in body["samples"]
    )

    after = await client.get(
        f"/projects/{pid}/artifacts",
        params={"type": "chunk_set"},
    )
    assert len(after.json()) == len(before.json())


@pytest.mark.skipif(not HAS_SEMCHUNK, reason="semchunk not installed")
async def test_unified_semchunk(client: AsyncClient) -> None:
    pid, clean_id = await _prep_clean(client)
    resp = await client.post(
        f"/projects/{pid}/chunk-sets",
        json={
            "clean_corpus_id": clean_id,
            "provider": "semchunk",
            "chunk_size": 8,
            "token_counter": "words",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["chunk_count"] >= 1


@pytest.mark.skipif(not HAS_CHUNKLET, reason="chunklet not installed")
async def test_unified_chunklet_document(client: AsyncClient) -> None:
    pid, clean_id = await _prep_clean(client)
    resp = await client.post(
        f"/projects/{pid}/chunk-sets",
        json={
            "clean_corpus_id": clean_id,
            "provider": "chunklet",
            "mode": "document",
            "lang": "en",
            "max_sentences": 2,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["chunk_count"] >= 1


async def test_chunklet_missing_constraint_400(client: AsyncClient) -> None:
    pid, clean_id = await _prep_clean(client)
    resp = await client.post(
        f"/projects/{pid}/chunk-sets",
        json={
            "clean_corpus_id": clean_id,
            "provider": "chunklet",
            "mode": "document",
        },
    )
    assert resp.status_code == 400

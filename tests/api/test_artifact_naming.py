"""Artifact display names from source documents."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_api.services.artifact_naming import (
    display_name,
    source_name_from_filename,
)
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


def test_source_name_from_cyrillic_filename() -> None:
    assert (
        source_name_from_filename("Устав несения службы.pdf")
        == "Устав_несения_службы"
    )
    assert display_name("raw_bundle", "Устав_несения_службы") == "raw_Устав_несения_службы"
    assert (
        display_name("clean_corpus", "Устав_несения_службы")
        == "clean_Устав_несения_службы"
    )


async def test_upload_and_prep_carry_display_name(client: AsyncClient) -> None:
    pid = (await client.post("/projects", json={"name": "Naming"})).json()["id"]

    upload = await client.post(
        f"/projects/{pid}/raw-bundles",
        files=[
            (
                "files",
                (
                    "Устав несения службы.txt",
                    "Текст устава о несении службы.\n".encode("utf-8"),
                    "text/plain",
                ),
            )
        ],
    )
    assert upload.status_code == 201, upload.text
    raw = upload.json()["artifact"]
    assert raw["meta"]["source_name"] == "Устав_несения_службы"
    assert raw["meta"]["display_name"] == "raw_Устав_несения_службы"

    prep = await client.post(
        f"/projects/{pid}/prep",
        json={"raw_bundle_id": raw["id"], "pipeline": "plaintext"},
    )
    assert prep.status_code == 201, prep.text
    clean = prep.json()["artifact"]
    assert clean["meta"]["display_name"] == "clean_Устав_несения_службы"

    chunked = await client.post(
        f"/projects/{pid}/chunk-sets/reference",
        json={"clean_corpus_id": clean["id"], "size": 64, "overlap": 8},
    )
    assert chunked.status_code == 201, chunked.text
    assert (
        chunked.json()["artifact"]["meta"]["display_name"]
        == "chunks_Устав_несения_службы"
    )

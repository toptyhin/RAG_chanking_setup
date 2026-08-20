"""Versioned prompt store and API."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rageval_api.main import create_app
from rageval_domain.settings import get_settings
from rageval_llm_providers import (
    DOCUMENT_PLACEHOLDER,
    SCHEMA_PLACEHOLDER,
    PROMPT_ID_RAG_QUESTION_PREP,
    PromptStore,
    default_question_prep_schema,
)


def test_prompt_store_versions_and_render(tmp_path: Path) -> None:
    store = PromptStore(tmp_path / "prompts.json")
    prompt = store.get(PROMPT_ID_RAG_QUESTION_PREP)
    assert prompt.active_version == 1
    assert DOCUMENT_PLACEHOLDER in prompt.active_body()
    assert SCHEMA_PLACEHOLDER in prompt.active_body()

    updated = store.save_new_version(
        PROMPT_ID_RAG_QUESTION_PREP,
        f"Ask questions.\n{DOCUMENT_PLACEHOLDER}\n{SCHEMA_PLACEHOLDER}\n",
        note="shorter",
    )
    assert updated.active_version == 2
    assert len(updated.versions) == 2

    store.set_active_version(PROMPT_ID_RAG_QUESTION_PREP, 1)
    assert store.get(PROMPT_ID_RAG_QUESTION_PREP).active_version == 1

    rendered = store.render_active(
        PROMPT_ID_RAG_QUESTION_PREP,
        document="DOC BODY",
    )
    assert "DOC BODY" in rendered
    assert DOCUMENT_PLACEHOLDER not in rendered
    assert SCHEMA_PLACEHOLDER not in rendered
    assert '"questions"' in rendered
    assert '"enum"' in rendered or "L1" in rendered


def test_prompt_store_migrates_old_body_without_schema_placeholder(
    tmp_path: Path,
) -> None:
    import json

    path = tmp_path / "prompts.json"
    # Write legacy catalog directly (bypass store.load migration).
    path.write_text(
        json.dumps(
            {
                "prompts": [
                    {
                        "id": PROMPT_ID_RAG_QUESTION_PREP,
                        "name": "RAG question prep",
                        "description": "",
                        "active_version": 1,
                        "versions": [
                            {
                                "version": 1,
                                "body": f"Old prompt.\n{DOCUMENT_PLACEHOLDER}\n",
                                "created_at": "2026-01-01T00:00:00+00:00",
                                "note": "legacy",
                            }
                        ],
                        "response_schema": {
                            "type": "object",
                            "properties": {"questions": {"type": "array"}},
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    migrated = PromptStore(path).get(PROMPT_ID_RAG_QUESTION_PREP)
    assert migrated.active_version == 2
    assert SCHEMA_PLACEHOLDER in migrated.active_body()
    assert migrated.response_schema == default_question_prep_schema()


def test_prompt_store_reset(tmp_path: Path) -> None:
    store = PromptStore(tmp_path / "prompts.json")
    store.save_new_version(
        PROMPT_ID_RAG_QUESTION_PREP,
        f"custom only\n{DOCUMENT_PLACEHOLDER}\n{SCHEMA_PLACEHOLDER}\n",
        note="x",
    )
    reset = store.reset_to_default(PROMPT_ID_RAG_QUESTION_PREP)
    assert reset.active_version == 3
    assert DOCUMENT_PLACEHOLDER in reset.active_body()
    assert SCHEMA_PLACEHOLDER in reset.active_body()
    assert reset.response_schema == default_question_prep_schema()


def test_prompt_store_response_schema(tmp_path: Path) -> None:
    store = PromptStore(tmp_path / "prompts.json")
    prompt = store.get(PROMPT_ID_RAG_QUESTION_PREP)
    assert prompt.response_schema["required"] == ["questions"]

    custom = {
        "type": "object",
        "properties": {
            "questions": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["questions"],
    }
    updated = store.set_response_schema(PROMPT_ID_RAG_QUESTION_PREP, custom)
    assert updated.response_schema == custom
    assert store.active_response_schema(PROMPT_ID_RAG_QUESTION_PREP) == custom

    with pytest.raises(ValueError, match="object"):
        store.set_response_schema(
            PROMPT_ID_RAG_QUESTION_PREP,
            {"type": "array", "items": {"type": "string"}},
        )

@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "rageval.db"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    get_settings.cache_clear()


async def test_prompts_api_list_and_version(client: AsyncClient) -> None:
    listed = await client.get("/prompts")
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert len(body["prompts"]) >= 1
    ids = {p["id"] for p in body["prompts"]}
    assert PROMPT_ID_RAG_QUESTION_PREP in ids

    got = await client.get(f"/prompts/{PROMPT_ID_RAG_QUESTION_PREP}")
    assert got.status_code == 200
    prompt = got.json()
    assert prompt["active_version"] == 1
    assert prompt["document_placeholder"] == DOCUMENT_PLACEHOLDER
    assert prompt["schema_placeholder"] == SCHEMA_PLACEHOLDER
    assert prompt["response_schema"]["required"] == ["questions"]
    assert prompt["response_schema"]["properties"]["questions"]["minItems"] == 12

    saved = await client.post(
        f"/prompts/{PROMPT_ID_RAG_QUESTION_PREP}/versions",
        json={
            "body": f"v2 body\n{DOCUMENT_PLACEHOLDER}\n{SCHEMA_PLACEHOLDER}\n",
            "note": "api",
            "response_schema": {
                "type": "object",
                "properties": {"questions": {"type": "array"}},
                "required": ["questions"],
            },
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["active_version"] == 2
    assert saved.json()["response_schema"]["required"] == ["questions"]

    schema_put = await client.put(
        f"/prompts/{PROMPT_ID_RAG_QUESTION_PREP}/schema",
        json={
            "response_schema": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {"type": "object"},
                    }
                },
                "required": ["questions"],
            }
        },
    )
    assert schema_put.status_code == 200, schema_put.text
    assert "items" in schema_put.json()["response_schema"]["properties"]["questions"]

    bad_schema = await client.put(
        f"/prompts/{PROMPT_ID_RAG_QUESTION_PREP}/schema",
        json={"response_schema": {"type": "array"}},
    )
    assert bad_schema.status_code == 400

    activated = await client.put(
        f"/prompts/{PROMPT_ID_RAG_QUESTION_PREP}/active",
        json={"version": 1},
    )
    assert activated.status_code == 200
    assert activated.json()["active_version"] == 1

    reset = await client.post(f"/prompts/{PROMPT_ID_RAG_QUESTION_PREP}/reset")
    assert reset.status_code == 200
    assert reset.json()["active_version"] == 3
    assert DOCUMENT_PLACEHOLDER in reset.json()["active_body"]
    assert reset.json()["response_schema"]["required"] == ["questions"]


async def test_prompts_api_404(client: AsyncClient) -> None:
    missing = await client.get("/prompts/does-not-exist")
    assert missing.status_code == 404

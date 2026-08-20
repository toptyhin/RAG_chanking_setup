"""POST /projects/{id}/test-sets/prepare with stubbed LLM."""

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
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    get_settings.cache_clear()


async def _seed_project_with_corpus(client: AsyncClient) -> tuple[str, str, str]:
    created = await client.post("/projects", json={"name": "prep-q"})
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    # Minimal raw → prep → clean_corpus via plaintext path is heavy;
    # use reference chunking after inventing clean via chunk import parents.
    # Seed clean_corpus by running prep on an uploaded raw file.
    files = {
        "files": ("policy.txt", b"The return window is 30 days from purchase.\n", "text/plain"),
    }
    raw = await client.post(f"/projects/{project_id}/raw-bundles", files=files)
    assert raw.status_code == 201, raw.text
    raw_id = raw.json()["artifact"]["id"]

    prep = await client.post(
        f"/projects/{project_id}/prep",
        json={"raw_bundle_id": raw_id, "pipeline": "plaintext"},
    )
    assert prep.status_code == 201, prep.text
    clean_id = prep.json()["artifact"]["id"]

    chunks = await client.post(
        f"/projects/{project_id}/chunk-sets/reference",
        json={"clean_corpus_id": clean_id, "size": 64, "overlap": 16},
    )
    assert chunks.status_code == 201, chunks.text
    chunk_set_id = chunks.json()["artifact"]["id"]
    return project_id, clean_id, chunk_set_id


async def test_prepare_questions_uses_clean_corpus_not_chunks(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id, clean_id, chunk_set_id = await _seed_project_with_corpus(client)

    class StubProvider:
        def list_models(self) -> list[str]:
            return ["stub"]

        def ping(self):  # pragma: no cover
            raise NotImplementedError

        def get_model_limits(self):
            from rageval_llm_providers.limits import ModelLimits

            return ModelLimits(model="stub", context_length=128_000, source="test")

        def generate(self, prompt: str, *, response_format=None) -> str:
            # Must contain clean document text; must NOT look like overlapped chunk dump.
            assert "30 days" in prompt
            assert "{{document}}" not in prompt
            assert "[c_" not in prompt  # chunk ids not injected into document
            assert response_format is not None
            assert response_format.get("required") == ["questions"]
            assert response_format["properties"]["questions"]["minItems"] == 12
            questions = []
            for level in ("L1", "L2", "L3", "L4"):
                for i in range(3):
                    questions.append(
                        {
                            "level": level,
                            "question": f"{level} question {i} about return window?",
                            "expected_answer": "30 days",
                            "source_quote": "The return window is 30 days from purchase.",
                            "evidence_quotes": [
                                "The return window is 30 days from purchase."
                            ],
                        }
                    )
            import json

            return json.dumps({"questions": questions})

    monkeypatch.setattr(
        "rageval_api.routes.testsets.build_provider",
        lambda _config: StubProvider(),
    )

    prepared = await client.post(
        f"/projects/{project_id}/test-sets/prepare",
        json={"clean_corpus_id": clean_id, "chunk_set_id": chunk_set_id},
    )
    assert prepared.status_code == 200, prepared.text
    body = prepared.json()
    assert body["clean_corpus_id"] == clean_id
    assert body["document_count"] >= 1
    assert body["chunk_set_id"] == chunk_set_id
    assert body["part_count"] == 1
    assert len(body["questions"]) == 12
    assert body["questions"][0]["text"].startswith("L1")
    assert body["prompt_id"] == "rag_question_prep"


async def test_prepare_questions_splits_oversized_document(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id, clean_id, chunk_set_id = await _seed_project_with_corpus(client)
    calls: list[dict] = []

    class StubProvider:
        def list_models(self) -> list[str]:
            return ["stub"]

        def ping(self):  # pragma: no cover
            raise NotImplementedError

        def get_model_limits(self):
            from rageval_llm_providers.limits import ModelLimits

            # Large enough for the template overhead + several mid-size parts.
            return ModelLimits(model="stub", context_length=12_000, source="test")

        def generate(self, prompt: str, *, response_format=None) -> str:
            import json

            n = int(response_format["properties"]["questions"]["minItems"])
            calls.append({"n": n, "prompt_len": len(prompt)})
            questions = []
            levels = ["L1", "L2", "L3", "L4"]
            for i in range(n):
                level = levels[i % 4]
                questions.append(
                    {
                        "level": level,
                        "question": f"PartQ {len(calls)}-{i}?",
                        "expected_answer": "A",
                        "source_quote": "quote",
                        "evidence_quotes": ["quote"],
                    }
                )
            return json.dumps({"questions": questions})

    # Inflate clean corpus text via monkeypatch of document builder.
    big = ("Параграф про возврат товара и условия доставки. " * 40 + "\n\n") * 30

    monkeypatch.setattr(
        "rageval_api.routes.testsets._document_from_corpus",
        lambda _corpus: (big, 1),
    )
    monkeypatch.setattr(
        "rageval_api.routes.testsets.build_provider",
        lambda _config: StubProvider(),
    )

    prepared = await client.post(
        f"/projects/{project_id}/test-sets/prepare",
        json={"clean_corpus_id": clean_id, "chunk_set_id": chunk_set_id},
    )
    assert prepared.status_code == 200, prepared.text
    body = prepared.json()
    assert body["part_count"] >= 2
    assert body["part_count"] <= 12
    assert len(calls) == body["part_count"]
    assert sum(c["n"] for c in calls) == 12
    assert len(body["questions"]) == 12

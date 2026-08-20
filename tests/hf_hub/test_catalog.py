"""HF Hub catalog unit tests (mocked HTTP)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from rageval_hf_hub import HfHubCatalog
from rageval_hf_hub.catalog import (
    _extract_size_bytes,
    _is_st_embedding,
    _looks_like_cross_encoder,
    _parse_model,
)


def test_extract_size_bytes_prefers_used_storage() -> None:
    assert _extract_size_bytes({"usedStorage": 1_500_000_000}) == 1_500_000_000
    assert (
        _extract_size_bytes(
            {
                "siblings": [
                    {"rfilename": "a.safetensors", "size": 100},
                    {"rfilename": "b.bin", "lfs": {"size": 50}},
                ]
            }
        )
        == 150
    )
    assert _extract_size_bytes({}) is None


def test_get_used_storage_uses_single_expand(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: Any) -> bool:
            return False

        def get(self, url: str, params: Any = None) -> httpx.Response:
            captured["url"] = url
            captured["params"] = params
            req = httpx.Request("GET", url)
            return httpx.Response(
                200,
                request=req,
                json={"id": "org/model", "usedStorage": 42},
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    size = HfHubCatalog().get_used_storage("org/model")
    assert size == 42
    assert captured["params"] == {"expand": "usedStorage"}


def test_parse_and_cross_encoder_heuristic() -> None:
    emb = _parse_model(
        {
            "id": "sentence-transformers/all-MiniLM-L6-v2",
            "downloads": 100,
            "likes": 2,
            "pipeline_tag": "feature-extraction",
            "tags": ["sentence-transformers"],
            "library_name": "sentence-transformers",
        }
    )
    assert emb.id.endswith("MiniLM-L6-v2")
    assert not _looks_like_cross_encoder(emb)

    ce = _parse_model(
        {
            "id": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "downloads": 50,
            "likes": 1,
            "pipeline_tag": "text-ranking",
            "tags": ["sentence-transformers", "cross-encoder"],
            "library_name": "sentence-transformers",
        }
    )
    assert _looks_like_cross_encoder(ce)


def test_search_embedding_uses_pipeline_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: Any) -> bool:
            return False

        def get(self, url: str, params: dict | None = None) -> httpx.Response:
            captured["url"] = url
            captured["params"] = dict(params or {})
            req = httpx.Request("GET", url, params=params)
            return httpx.Response(
                200,
                request=req,
                json=[
                    {
                        "id": "sentence-transformers/all-MiniLM-L6-v2",
                        "downloads": 10,
                        "likes": 1,
                        "pipeline_tag": "feature-extraction",
                        "tags": ["sentence-transformers"],
                        "library_name": "sentence-transformers",
                    }
                ],
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    items = HfHubCatalog().search("embedding", query="minilm", limit=10)
    assert captured["params"]["pipeline_tag"] == "feature-extraction"
    assert captured["params"]["search"] == "minilm"
    assert items[0].id.endswith("MiniLM-L6-v2")


def test_st_embedding_requires_library_name() -> None:
    ok = _parse_model(
        {
            "id": "unsloth/Qwen3-Embedding-0.6B",
            "library_name": "sentence-transformers",
            "pipeline_tag": "feature-extraction",
            "tags": ["sentence-transformers"],
        }
    )
    assert _is_st_embedding(ok)

    mlx = _parse_model(
        {
            "id": "mlx-community/Qwen3-Embedding-0.6B",
            "library_name": "mlx",
            "pipeline_tag": "feature-extraction",
            "tags": ["sentence-transformers", "mlx"],
        }
    )
    assert not _is_st_embedding(mlx)

    gguf = _parse_model(
        {
            "id": "mradermacher/Qwen3-Embedding-0.6B-GGUF",
            "library_name": "sentence-transformers",
            "pipeline_tag": "feature-extraction",
            "tags": ["sentence-transformers", "gguf"],
        }
    )
    assert not _is_st_embedding(gguf)


def test_search_embedding_filters_non_st(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: Any) -> bool:
            return False

        def get(self, url: str, params: dict | None = None) -> httpx.Response:
            req = httpx.Request("GET", url, params=params)
            return httpx.Response(
                200,
                request=req,
                json=[
                    {
                        "id": "mlx-community/foo",
                        "downloads": 99,
                        "likes": 1,
                        "pipeline_tag": "feature-extraction",
                        "tags": ["sentence-transformers", "mlx"],
                        "library_name": "mlx",
                    },
                    {
                        "id": "org/real-st",
                        "downloads": 10,
                        "likes": 1,
                        "pipeline_tag": "feature-extraction",
                        "tags": ["sentence-transformers"],
                        "library_name": "sentence-transformers",
                    },
                ],
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    items = HfHubCatalog().search("embedding", query="qwen", limit=10)
    assert [m.id for m in items] == ["org/real-st"]


def test_search_rerank_filters_cross_encoders(monkeypatch: pytest.MonkeyPatch) -> None:

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: Any) -> bool:
            return False

        def get(self, url: str, params: dict | None = None) -> httpx.Response:
            req = httpx.Request("GET", url, params=params)
            return httpx.Response(
                200,
                request=req,
                json=[
                    {
                        "id": "sentence-transformers/all-MiniLM-L6-v2",
                        "downloads": 10,
                        "likes": 1,
                        "pipeline_tag": "feature-extraction",
                        "tags": ["sentence-transformers"],
                        "library_name": "sentence-transformers",
                    },
                    {
                        "id": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                        "downloads": 9,
                        "likes": 1,
                        "pipeline_tag": "text-ranking",
                        "tags": ["sentence-transformers", "cross-encoder"],
                        "library_name": "sentence-transformers",
                    },
                ],
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    items = HfHubCatalog().search("rerank", query="", limit=10)
    assert [m.id for m in items] == ["cross-encoder/ms-marco-MiniLM-L-6-v2"]

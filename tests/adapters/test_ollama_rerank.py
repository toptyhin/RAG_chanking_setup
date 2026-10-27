"""Ollama generative reranker (mocked HTTP) + rerank provider config."""

from __future__ import annotations

import json
import math

import httpx
import pytest

from rageval_llm_providers.rerank import (
    OllamaGenerativeRerankProvider,
    RerankConfig,
    RerankConfigStore,
    RerankProviderKind,
    build_qwen3_rerank_prompt,
    infer_rerank_provider,
    resolve_rerank_provider,
)
from rageval_rerank import RerankCandidate

_RealClient = httpx.Client


def _handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode("utf-8"))
    if request.url.path == "/api/show":
        name = str(body.get("name", ""))
        capabilities = ["embedding"] if "embedding-only" in name else [
            "completion",
            "thinking",
        ]
        return httpx.Response(200, json={"capabilities": capabilities})
    if request.url.path == "/api/generate":
        prompt = str(body.get("prompt", ""))
        relevant = "Paris" in prompt
        payload = {
            "response": "yes" if relevant else "No",
            "logprobs": [
                {
                    "token": "yes" if relevant else "No",
                    "logprob": -0.1 if relevant else -0.2,
                }
            ],
        }
        if "no-logprobs" in str(body.get("model", "")):
            payload.pop("logprobs")
        return httpx.Response(200, json=payload)
    return httpx.Response(404, json={"error": "not found"})


def _patch_client(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = httpx.MockTransport(_handler)

    def _client(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return _RealClient(*args, **kwargs)

    monkeypatch.setattr(
        "rageval_llm_providers.rerank.httpx.Client",
        _client,
    )


def _provider(
    monkeypatch: pytest.MonkeyPatch,
    model: str = "reranker:latest",
) -> OllamaGenerativeRerankProvider:
    _patch_client(monkeypatch)
    return OllamaGenerativeRerankProvider(
        base_url="http://ollama.test",
        model=model,
    )


def test_scores_relevant_candidate_above_irrelevant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(monkeypatch)
    scores = provider.score(
        "What is the capital of France?",
        [
            RerankCandidate(chunk_id="a", text="Paris is the capital of France."),
            RerankCandidate(chunk_id="b", text="The internal service charter."),
        ],
    )
    assert scores[0] > scores[1]
    assert scores[0] == pytest.approx(math.exp(-0.1))
    assert scores[1] == pytest.approx(-math.exp(-0.2))
    assert scores[0] > 0 > scores[1]


def test_rejects_embedding_only_ollama_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="cannot generate text"):
        _provider(monkeypatch, model="embedding-only:latest")


def test_scores_without_logprobs_fall_back_to_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(monkeypatch, model="no-logprobs:latest")
    scores = provider.score(
        "What is the capital of France?",
        [RerankCandidate(chunk_id="a", text="Paris is the capital of France.")],
    )
    assert scores == [1.0]


def test_qwen3_rerank_prompt_contains_query_and_document() -> None:
    prompt = build_qwen3_rerank_prompt("query text", "document text")
    assert "<Query>: query text" in prompt
    assert "<Document>: document text" in prompt
    assert prompt.endswith("<think>\n\n</think>\n\n")


def test_rerank_config_store_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = RerankConfigStore(tmp_path / "rerank_config.json")
    assert store.load_or_none() is None

    store.merge_update({"provider": "ollama", "model": "qwen3:latest"})
    config = store.load_or_none()
    assert config is not None
    assert config.provider is RerankProviderKind.ollama
    assert config.model == "qwen3:latest"


def test_rerank_provider_inference_and_explicit_config() -> None:
    assert infer_rerank_provider("qwen3-embedding:4b") is RerankProviderKind.ollama
    assert (
        infer_rerank_provider("cross-encoder/ms-marco-MiniLM-L-6-v2")
        is RerankProviderKind.huggingface
    )
    explicit = RerankConfig(
        provider=RerankProviderKind.huggingface,
        model="qwen3:latest",
    )
    assert (
        resolve_rerank_provider(explicit, "qwen3:latest")
        is RerankProviderKind.huggingface
    )

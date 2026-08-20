"""Ollama remote embed encode (mocked HTTP)."""

from __future__ import annotations

import json

import httpx
import numpy as np
import pytest

from rageval_embedding_providers.config import OllamaEmbeddingSettings
from rageval_embedding_providers.ollama import OllamaEmbeddingClient
from rageval_embedding_providers.remote_provider import RemoteEmbeddingProvider

_RealClient = httpx.Client


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/embed":
        body = json.loads(request.content.decode("utf-8"))
        inputs = body.get("input")
        if isinstance(inputs, str):
            inputs = [inputs]
        assert isinstance(inputs, list)
        # Deterministic non-unit vectors so L2-normalize is observable.
        rows = [[float(i + 1), 0.0, 0.0] for i, _ in enumerate(inputs)]
        return httpx.Response(200, json={"embeddings": rows})
    return httpx.Response(404, json={"error": "not found"})


def _patch_client(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = httpx.MockTransport(_handler)

    def _client(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return _RealClient(*args, **kwargs)

    monkeypatch.setattr(
        "rageval_embedding_providers.ollama.httpx.Client",
        _client,
    )


def test_ollama_encode_batch_l2_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch)
    client = OllamaEmbeddingClient(
        OllamaEmbeddingSettings(base_url="http://ollama.test", model="nomic-embed-text:latest")
    )
    vectors = client.encode(["a", "b"])
    assert vectors.shape == (2, 3)
    assert vectors.dtype == np.float32
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)
    assert vectors[0, 0] == pytest.approx(1.0)
    assert vectors[1, 0] == pytest.approx(1.0)


def test_remote_embedding_provider_probes_dimension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_client(monkeypatch)
    client = OllamaEmbeddingClient(
        OllamaEmbeddingSettings(base_url="http://ollama.test", model="nomic-embed-text")
    )
    provider = RemoteEmbeddingProvider(client, model_name="nomic-embed-text")
    assert provider.model_name == "nomic-embed-text"
    assert provider.dimension == 3
    empty = provider.encode([])
    assert empty.shape == (0, 3)
    batch = provider.encode(["x", "y"])
    assert batch.shape == (2, 3)

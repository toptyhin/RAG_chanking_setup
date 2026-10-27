"""RemoteEmbeddingProvider batching / retry and remote HTTP settings."""

from __future__ import annotations

import httpx
import numpy as np
import pytest

from rageval_embedding_providers.config import EmbeddingConfig, EmbeddingProviderKind
from rageval_embedding_providers.factory import (
    build_remote_client,
    remote_embed_batch_size,
    remote_embed_timeout_sec,
)
from rageval_embedding_providers.remote_provider import RemoteEmbeddingProvider


class _RecordingClient:
    def __init__(self, *, dimension: int = 4) -> None:
        self.calls: list[list[str]] = []
        self.dimension = dimension
        self.fail_next: int = 0

    def encode(self, texts: list[str]) -> np.ndarray:
        self.calls.append(list(texts))
        if self.fail_next > 0:
            self.fail_next -= 1
            raise httpx.ReadTimeout("timed out")
        return np.asarray(
            [[float(len(text)) + 1.0] + [1.0] * (self.dimension - 1) for text in texts],
            dtype=np.float32,
        )


def test_remote_provider_splits_large_encode_into_batches() -> None:
    client = _RecordingClient()
    provider = RemoteEmbeddingProvider(client, model_name="test-model", batch_size=3)

    vectors = provider.encode(
        ["a", "bb", "ccc", "dddd", "eeeee", "ffffff", "ggggggg"]
    )

    assert vectors.shape == (7, 4)
    assert client.calls[0] == ["dimension-probe"]  # dimension probe
    assert [len(call) for call in client.calls[1:]] == [3, 3, 1]
    assert client.calls[1] == ["a", "bb", "ccc"]
    assert client.calls[3] == ["ggggggg"]


def test_remote_provider_retries_one_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "rageval_embedding_providers.remote_provider.time.sleep",
        lambda _seconds: None,
    )
    client = _RecordingClient()
    provider = RemoteEmbeddingProvider(client, model_name="test-model", batch_size=2)
    client.fail_next = 1

    vectors = provider.encode(["one", "two"])

    assert vectors.shape == (2, 4)
    assert client.calls == [["dimension-probe"], ["one", "two"], ["one", "two"]]


def test_remote_embed_settings_come_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGEVAL_EMBED_TIMEOUT_SEC", "7.5")
    monkeypatch.setenv("RAGEVAL_EMBED_BATCH_SIZE", "5")
    assert remote_embed_timeout_sec() == 7.5
    assert remote_embed_batch_size() == 5

    config = EmbeddingConfig(
        provider=EmbeddingProviderKind.ollama,
        ollama={"base_url": "http://ollama.test", "model": "qwen3-embedding:4b"},
    )
    client = build_remote_client(config)
    assert client is not None
    assert client.timeout == 7.5


def test_remote_embed_settings_fall_back_to_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAGEVAL_EMBED_TIMEOUT_SEC", raising=False)
    monkeypatch.delenv("RAGEVAL_EMBED_BATCH_SIZE", raising=False)
    monkeypatch.setenv("RAGEVAL_EMBED_BATCH_SIZE", "not-a-number")
    assert remote_embed_timeout_sec() == 120.0
    assert remote_embed_batch_size() == 32

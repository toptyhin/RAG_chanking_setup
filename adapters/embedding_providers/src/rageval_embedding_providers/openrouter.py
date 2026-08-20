"""OpenRouter (OpenAI-compatible) embedding client."""

from __future__ import annotations

import time

import httpx
import numpy as np

from rageval_embedding_providers.config import OpenRouterEmbeddingSettings
from rageval_embedding_providers.vectors import rows_to_normalized_matrix
from rageval_llm_providers.catalog import (
    ModelPurpose,
    RemoteModelInfo,
    filter_openrouter_models,
    openrouter_output_modality_param,
    parse_openrouter_model,
)
from rageval_llm_providers.protocol import ConnectionTestResult


class OpenRouterEmbeddingClient:
    def __init__(
        self, settings: OpenRouterEmbeddingSettings, *, timeout: float = 30.0
    ) -> None:
        self.settings = settings
        self.timeout = timeout

    @property
    def _base(self) -> str:
        return self.settings.base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key.strip()
        if not key:
            raise ValueError("OpenRouter API key is not configured")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://rageval.local",
            "X-Title": "rageval",
        }

    def list_model_infos(
        self, *, purpose: ModelPurpose = ModelPurpose.embeddings
    ) -> list[RemoteModelInfo]:
        params = {"output_modalities": openrouter_output_modality_param(purpose)}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self._base}/models",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") or []
        items: list[RemoteModelInfo] = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            parsed = parse_openrouter_model(raw)
            if parsed is not None:
                items.append(parsed)
        return filter_openrouter_models(items, purpose=purpose)

    def list_models(self) -> list[str]:
        return [m.id for m in self.list_model_infos(purpose=ModelPurpose.embeddings)]

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self._base}/embeddings",
                headers=self._headers(),
                json={
                    "model": self.settings.model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") or []
        if not isinstance(data, list) or not data:
            raise RuntimeError("OpenRouter /embeddings returned empty data")
        indexed: list[tuple[int, list[float]]] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            emb = item.get("embedding")
            if not isinstance(emb, list) or not emb:
                raise RuntimeError("OpenRouter /embeddings returned empty embedding")
            idx = item.get("index", i)
            indexed.append((int(idx), [float(x) for x in emb]))
        indexed.sort(key=lambda pair: pair[0])
        rows = [row for _, row in indexed]
        if len(rows) != len(texts):
            raise RuntimeError(
                f"OpenRouter returned {len(rows)} embeddings for {len(texts)} texts"
            )
        return rows_to_normalized_matrix(rows)

    def ping(self) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self._base}/embeddings",
                    headers=self._headers(),
                    json={
                        "model": self.settings.model,
                        "input": "ping",
                    },
                )
                response.raise_for_status()
                payload = response.json()
            data = payload.get("data") or []
            dim = 0
            if data and isinstance(data[0], dict):
                emb = data[0].get("embedding")
                if isinstance(emb, list):
                    dim = len(emb)
            models = self.list_models()
            latency = (time.perf_counter() - started) * 1000.0
            return ConnectionTestResult(
                ok=True,
                latency_ms=latency,
                message=f"embed ok · dim {dim} · {len(models)} model(s) listed",
                model=self.settings.model,
                models=models[:50],
            )
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - started) * 1000.0
            return ConnectionTestResult(
                ok=False,
                latency_ms=latency,
                message=str(exc),
                model=self.settings.model,
            )

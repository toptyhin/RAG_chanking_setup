"""GigaChat embeddings HTTP client (OAuth + /embeddings ping + encode)."""

from __future__ import annotations

import time
import uuid

import httpx
import numpy as np

from rageval_embedding_providers.config import GigaChatEmbeddingSettings
from rageval_embedding_providers.vectors import rows_to_normalized_matrix
from rageval_llm_providers.ca import httpx_verify_arg
from rageval_llm_providers.catalog import (
    ModelPurpose,
    RemoteModelInfo,
    filter_gigachat_models,
    parse_gigachat_model,
)
from rageval_llm_providers.protocol import ConnectionTestResult


class GigaChatEmbeddingClient:
    def __init__(
        self, settings: GigaChatEmbeddingSettings, *, timeout: float = 30.0
    ) -> None:
        self.settings = settings
        self.timeout = timeout

    def _token(self, client: httpx.Client) -> str:
        credentials = self.settings.credentials.strip()
        if not credentials:
            raise ValueError("GigaChat credentials (authorization key) are not configured")
        response = client.post(
            self.settings.auth_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"scope": self.settings.scope},
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("GigaChat OAuth response missing access_token")
        return token

    def _fetch_raw_models(self) -> list:
        verify = httpx_verify_arg(verify_ssl=self.settings.verify_ssl)
        with httpx.Client(timeout=self.timeout, verify=verify) as client:
            token = self._token(client)
            base = self.settings.base_url.rstrip("/")
            response = client.get(
                f"{base}/models",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") or payload.get("models") or []
        return list(data) if isinstance(data, list) else []

    def list_model_infos(
        self, *, purpose: ModelPurpose = ModelPurpose.embeddings
    ) -> list[RemoteModelInfo]:
        items: list[RemoteModelInfo] = []
        for raw in self._fetch_raw_models():
            parsed = parse_gigachat_model(raw)
            if parsed is not None:
                items.append(parsed)
        return filter_gigachat_models(items, purpose=purpose)

    def list_models(self) -> list[str]:
        return [m.id for m in self.list_model_infos(purpose=ModelPurpose.embeddings)]

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        verify = httpx_verify_arg(verify_ssl=self.settings.verify_ssl)
        with httpx.Client(timeout=self.timeout, verify=verify) as client:
            token = self._token(client)
            base = self.settings.base_url.rstrip("/")
            response = client.post(
                f"{base}/embeddings",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "model": self.settings.model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") or []
        if not isinstance(data, list) or not data:
            raise RuntimeError("GigaChat /embeddings returned empty data")
        indexed: list[tuple[int, list[float]]] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            emb = item.get("embedding")
            if not isinstance(emb, list) or not emb:
                raise RuntimeError("GigaChat /embeddings returned empty embedding")
            idx = item.get("index", i)
            indexed.append((int(idx), [float(x) for x in emb]))
        indexed.sort(key=lambda pair: pair[0])
        rows = [row for _, row in indexed]
        if len(rows) != len(texts):
            raise RuntimeError(
                f"GigaChat returned {len(rows)} embeddings for {len(texts)} texts"
            )
        return rows_to_normalized_matrix(rows)

    def ping(self) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            verify = httpx_verify_arg(verify_ssl=self.settings.verify_ssl)
            with httpx.Client(timeout=self.timeout, verify=verify) as client:
                token = self._token(client)
                base = self.settings.base_url.rstrip("/")
                response = client.post(
                    f"{base}/embeddings",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
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
                message=f"embed ok · dim {dim} · OAuth + models ({len(models)})",
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

"""Ollama embedding HTTP client (tags + /api/embeddings ping + encode)."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import numpy as np

from rageval_embedding_providers.config import OllamaEmbeddingSettings
from rageval_embedding_providers.vectors import rows_to_normalized_matrix
from rageval_llm_providers.catalog import ModelPurpose, RemoteModelInfo, ollama_model_infos
from rageval_llm_providers.protocol import ConnectionTestResult

logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    def __init__(self, settings: OllamaEmbeddingSettings, *, timeout: float = 30.0) -> None:
        self.settings = settings
        self.timeout = timeout

    @property
    def _base(self) -> str:
        return self.settings.base_url.rstrip("/")

    def list_models(self) -> list[str]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self._base}/api/tags")
            response.raise_for_status()
            payload = response.json()
        models = payload.get("models") or []
        names: list[str] = []
        for item in models:
            name = item.get("name") if isinstance(item, dict) else None
            if isinstance(name, str) and name:
                names.append(name)
        return names

    def _embedding_lengths(self, names: list[str]) -> dict[str, int]:
        from rageval_llm_providers.limits import embedding_length_from_ollama_show

        if not names:
            return {}

        def one(name: str) -> tuple[str, int | None]:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self._base}/api/show",
                        json={"name": name},
                    )
                    response.raise_for_status()
                    payload = response.json()
            except Exception:  # noqa: BLE001
                return name, None
            if not isinstance(payload, dict):
                return name, None
            dim, _src = embedding_length_from_ollama_show(payload)
            return name, dim

        out: dict[str, int] = {}
        workers = max(1, min(8, len(names)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(one, n) for n in names]
            for fut in as_completed(futures):
                try:
                    name, dim = fut.result()
                except Exception:  # noqa: BLE001
                    logger.debug("ollama show failed", exc_info=True)
                    continue
                if dim is not None and dim > 0:
                    out[name] = dim
        return out

    def list_model_infos(
        self, *, purpose: ModelPurpose = ModelPurpose.embeddings
    ) -> list[RemoteModelInfo]:
        names = self.list_models()
        dims: dict[str, int] = {}
        if purpose is ModelPurpose.embeddings:
            dims = self._embedding_lengths(names)
        return ollama_model_infos(names, dimensions_by_id=dims)

    def _embed_once(self, client: httpx.Client, text: str) -> list[float]:
        # Prefer modern /api/embed; fall back to legacy /api/embeddings.
        model = self.settings.model
        embed = client.post(
            f"{self._base}/api/embed",
            json={"model": model, "input": text},
        )
        if embed.status_code == 404:
            legacy = client.post(
                f"{self._base}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            legacy.raise_for_status()
            payload = legacy.json()
            vector = payload.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise RuntimeError("Ollama /api/embeddings returned empty embedding")
            return [float(x) for x in vector]

        embed.raise_for_status()
        payload = embed.json()
        embeddings = payload.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            first = embeddings[0]
            if isinstance(first, list) and first:
                return [float(x) for x in first]
        vector = payload.get("embedding")
        if isinstance(vector, list) and vector:
            return [float(x) for x in vector]
        raise RuntimeError("Ollama /api/embed returned empty embedding")

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        model = self.settings.model
        with httpx.Client(timeout=self.timeout) as client:
            embed = client.post(
                f"{self._base}/api/embed",
                json={"model": model, "input": texts},
            )
            if embed.status_code == 404:
                rows = [self._embed_once(client, text) for text in texts]
                return rows_to_normalized_matrix(rows)

            embed.raise_for_status()
            payload = embed.json()
            embeddings = payload.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                rows: list[list[float]] = []
                for item in embeddings:
                    if not isinstance(item, list) or not item:
                        raise RuntimeError("Ollama /api/embed returned empty embedding")
                    rows.append([float(x) for x in item])
                if len(rows) != len(texts):
                    raise RuntimeError(
                        f"Ollama returned {len(rows)} embeddings for {len(texts)} texts"
                    )
                return rows_to_normalized_matrix(rows)
            # Single-vector response shape (rare for batch).
            vector = payload.get("embedding")
            if isinstance(vector, list) and vector and len(texts) == 1:
                return rows_to_normalized_matrix([[float(x) for x in vector]])
        raise RuntimeError("Ollama /api/embed returned empty embeddings")

    def ping(self) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            models = self.list_models()
            with httpx.Client(timeout=self.timeout) as client:
                vector = self._embed_once(client, "ping")
            latency = (time.perf_counter() - started) * 1000.0
            chosen = self.settings.model
            if chosen and chosen not in models and models:
                hint = (
                    f"embed ok · dim {len(vector)}; "
                    f"model {chosen!r} not in tags ({len(models)} listed)"
                )
            else:
                hint = f"embed ok · dim {len(vector)} · model {chosen}"
            return ConnectionTestResult(
                ok=True,
                latency_ms=latency,
                message=hint,
                model=chosen or (models[0] if models else None),
                models=models[:50],
            )
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - started) * 1000.0
            message = str(exc)
            lowered = message.lower()
            if "connection refused" in lowered or "errno 111" in lowered:
                host = self._base
                if "localhost" in host or "127.0.0.1" in host:
                    message = (
                        f"{message}. API cannot reach Ollama at {host}. "
                        "In Docker Compose use http://host.docker.internal:11435 "
                        "(ollama-proxy → host 127.0.0.1:11434), not localhost."
                    )
                elif ":11434" in host:
                    message = (
                        f"{message}. Direct host :11434 is unreachable from Docker "
                        "while Ollama binds 127.0.0.1. Use http://host.docker.internal:11435 "
                        "and ensure the ollama-proxy compose service is running."
                    )
            return ConnectionTestResult(
                ok=False,
                latency_ms=latency,
                message=message,
                model=self.settings.model,
            )

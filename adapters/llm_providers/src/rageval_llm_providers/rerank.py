"""Reranker provider selection + Ollama generative reranker.

Ollama has no native rerank endpoint, so a reranker served by Ollama is used as a
generative cross-encoder: for every (query, candidate) pair we ask a
completion-capable model to answer yes/no and turn the token probability into a
relevance score. This is exactly how Qwen3-Reranker models are meant to be
evaluated (logit of "yes" vs "no").
"""

from __future__ import annotations

import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from rageval_llm_providers.config import write_json_atomic
from rageval_rerank import RerankCandidate

logger = logging.getLogger(__name__)

RERANK_INSTRUCT = (
    "Given a web search query, retrieve relevant passages that answer the query"
)


class RerankProviderKind(StrEnum):
    huggingface = "huggingface"
    ollama = "ollama"
    openrouter = "openrouter"
    gigachat = "gigachat"


class RerankConfig(BaseModel):
    """Which runtime scores rerank candidates (model id comes from the run/lab)."""

    provider: RerankProviderKind = RerankProviderKind.huggingface
    model: str = ""


class RerankConfigStore:
    """Persist rerank provider selection (JSON under DATA_DIR)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> RerankConfig:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return RerankConfig()
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("invalid JSON in %s (%s); using defaults", self.path, exc)
            return RerankConfig()
        if not isinstance(raw, dict):
            logger.warning("%s is not a JSON object; using defaults", self.path)
            return RerankConfig()
        return RerankConfig.model_validate(raw)

    def load_or_none(self) -> RerankConfig | None:
        if not self.path.is_file():
            return None
        return self.load()

    def save(self, config: RerankConfig) -> None:
        write_json_atomic(self.path, config.model_dump(mode="json"))

    def merge_update(self, patch: dict[str, Any]) -> RerankConfig:
        current = self.load()
        data = current.model_dump(mode="json")
        for key, value in patch.items():
            if value is not None:
                data[key] = value
        updated = RerankConfig.model_validate(data)
        self.save(updated)
        return updated


def infer_rerank_provider(model_id: str) -> RerankProviderKind:
    """Backward-compatible guess for configs saved before the provider was persisted.

    Ollama tag names always carry a ``:tag`` suffix (e.g. ``qwen3-embedding:4b``),
    while Hugging Face repo ids cannot contain ``:``.
    """
    mid = model_id.strip()
    if ":" in mid:
        return RerankProviderKind.ollama
    return RerankProviderKind.huggingface


def resolve_rerank_provider(
    config: RerankConfig | None,
    model_id: str,
) -> RerankProviderKind:
    """Explicit saved provider wins; otherwise infer from the model id."""
    if config is not None:
        return RerankProviderKind(config.provider)
    return infer_rerank_provider(model_id)


def build_qwen3_rerank_prompt(
    query: str,
    document: str,
    *,
    instruct: str = RERANK_INSTRUCT,
) -> str:
    """Official Qwen3-Reranker prompt; yes/no token follows the assistant prefix."""
    return (
        "<|im_start|>system\n"
        "Judge whether the Document meets the requirements based on the Query and "
        'the Instruct provided. Note that the answer can only be "yes" or "no".'
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"<Instruct>: {instruct}\n\n"
        f"<Query>: {query}\n\n"
        f"<Document>: {document}<|im_end|>\n"
        "<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


class OllamaGenerativeRerankProvider:
    """Score (query, candidate) pairs by asking an Ollama model for yes/no."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float = 120.0,
        max_workers: int = 4,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.timeout = timeout
        self.max_workers = max(1, int(max_workers))
        self._check_completion_support()

    def _check_completion_support(self) -> None:
        try:
            with httpx.Client(timeout=min(self.timeout, 30.0)) as client:
                response = client.post(
                    f"{self.base_url}/api/show",
                    json={"name": self.model_name},
                )
                if response.status_code == 404:
                    raise RuntimeError(
                        f"Ollama model {self.model_name!r} not found at {self.base_url}"
                    )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"cannot inspect Ollama model {self.model_name!r}: {exc}"
            ) from exc

        capabilities = payload.get("capabilities") if isinstance(payload, dict) else None
        if isinstance(capabilities, list) and capabilities and "completion" not in capabilities:
            listed = ", ".join(str(item) for item in capabilities)
            raise RuntimeError(
                f"Ollama model {self.model_name!r} cannot generate text "
                f"(capabilities: {listed}). Ollama has no rerank endpoint, so a "
                "reranker must be a completion-capable model "
                "(for example 'awenleven/Qwen3-Reranker-4B:Q4_K_M'). "
                "Classifier/embedding-only GGUF models cannot be used for rerank."
            )

    def score(self, query: str, candidates: list[RerankCandidate]) -> list[float]:
        if not candidates:
            return []
        workers = max(1, min(self.max_workers, len(candidates)))
        with httpx.Client(timeout=self.timeout) as client:
            if workers == 1:
                return [self._score_one(client, query, item) for item in candidates]
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(self._score_one, client, query, item)
                    for item in candidates
                ]
                return [future.result() for future in futures]

    def _score_one(
        self,
        client: httpx.Client,
        query: str,
        candidate: RerankCandidate,
    ) -> float:
        prompt = build_qwen3_rerank_prompt(query, candidate.text)
        try:
            response = client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "raw": True,
                    "stream": False,
                    "logprobs": True,
                    "options": {"num_predict": 1, "temperature": 0},
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Ollama rerank request failed for {self.model_name!r}: {exc}"
            ) from exc

        answer = str(payload.get("response") or "").strip().lower()
        probability = _chosen_token_probability(payload.get("logprobs"))
        if answer.startswith("yes"):
            # Positive and sorted by confidence: P("yes") in (0, 1].
            return probability if probability is not None else 1.0
        if answer.startswith("no"):
            # Negative so every "no" ranks below every "yes"; more confident
            # "no" (higher P("no")) gets a lower score.
            return -probability if probability is not None else 0.0
        return -1.0


def _chosen_token_probability(logprobs: Any) -> float | None:
    """P(chosen token) from Ollama's ``logprobs`` list; None if not reported."""
    if not isinstance(logprobs, list) or not logprobs:
        return None
    first = logprobs[0]
    if not isinstance(first, dict):
        return None
    value = first.get("logprob")
    if not isinstance(value, (int, float)):
        return None
    return min(1.0, math.exp(float(value)))


__all__ = [
    "OllamaGenerativeRerankProvider",
    "RERANK_INSTRUCT",
    "RerankConfig",
    "RerankConfigStore",
    "RerankProviderKind",
    "build_qwen3_rerank_prompt",
    "infer_rerank_provider",
    "resolve_rerank_provider",
]

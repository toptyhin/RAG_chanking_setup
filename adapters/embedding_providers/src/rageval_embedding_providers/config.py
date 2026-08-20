"""Persisted embedding-provider connection settings (JSON under DATA_DIR)."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from rageval_llm_providers.config import default_ollama_base_url, mask_secret


class EmbeddingProviderKind(StrEnum):
    ollama = "ollama"
    sentence_transformers = "sentence_transformers"
    openrouter = "openrouter"
    gigachat = "gigachat"


class SentenceTransformersSettings(BaseModel):
    model: str = "sentence-transformers/all-MiniLM-L6-v2"


class OllamaEmbeddingSettings(BaseModel):
    base_url: str = Field(default_factory=default_ollama_base_url)
    model: str = "nomic-embed-text"


class OpenRouterEmbeddingSettings(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    model: str = "openai/text-embedding-3-small"


class GigaChatEmbeddingSettings(BaseModel):
    credentials: str = ""
    scope: str = "GIGACHAT_API_PERS"
    base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    model: str = "Embeddings"
    verify_ssl: bool = True


class EmbeddingConfig(BaseModel):
    provider: EmbeddingProviderKind = EmbeddingProviderKind.sentence_transformers
    sentence_transformers: SentenceTransformersSettings = Field(
        default_factory=SentenceTransformersSettings
    )
    ollama: OllamaEmbeddingSettings = Field(default_factory=OllamaEmbeddingSettings)
    openrouter: OpenRouterEmbeddingSettings = Field(
        default_factory=OpenRouterEmbeddingSettings
    )
    gigachat: GigaChatEmbeddingSettings = Field(default_factory=GigaChatEmbeddingSettings)


class EmbeddingConfigStore:
    """Load / save embedding config from ``data_dir/embedding_config.json``."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> EmbeddingConfig:
        if not self.path.is_file():
            return EmbeddingConfig()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return EmbeddingConfig()
        return EmbeddingConfig.model_validate(raw)

    def save(self, config: EmbeddingConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="json")
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def merge_update(self, patch: dict[str, Any]) -> EmbeddingConfig:
        """Apply a partial update; blank secrets keep previously stored values."""
        current = self.load()
        data = current.model_dump(mode="json")

        if "provider" in patch and patch["provider"] is not None:
            data["provider"] = patch["provider"]

        for key in ("sentence_transformers", "ollama", "openrouter", "gigachat"):
            if key not in patch or patch[key] is None:
                continue
            section = patch[key]
            if not isinstance(section, dict):
                continue
            merged = dict(data.get(key) or {})
            for field, value in section.items():
                if field in {"api_key", "credentials"}:
                    if value is None:
                        continue
                    if isinstance(value, str) and value.strip() == "":
                        continue
                if value is not None:
                    merged[field] = value
            data[key] = merged

        updated = EmbeddingConfig.model_validate(data)
        self.save(updated)
        return updated


__all__ = [
    "EmbeddingConfig",
    "EmbeddingConfigStore",
    "EmbeddingProviderKind",
    "GigaChatEmbeddingSettings",
    "OllamaEmbeddingSettings",
    "OpenRouterEmbeddingSettings",
    "SentenceTransformersSettings",
    "mask_secret",
]

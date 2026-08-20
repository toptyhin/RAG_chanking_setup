"""Persisted text-LLM connection settings (JSON under DATA_DIR)."""

from __future__ import annotations

import json
import os
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TextLlmProvider(StrEnum):
    ollama = "ollama"
    openrouter = "openrouter"
    gigachat = "gigachat"


def default_ollama_base_url() -> str:
    """Prefer env; inside Docker use host proxy port (compose ollama-proxy)."""
    env = os.environ.get("OLLAMA_BASE_URL", "").strip()
    if env:
        return env.rstrip("/")
    if Path("/.dockerenv").is_file():
        # Compose maps host 127.0.0.1:11434 → :11435 via ollama-proxy (network_mode: host)
        return "http://host.docker.internal:11435"
    return "http://localhost:11434"


class OllamaSettings(BaseModel):
    base_url: str = Field(default_factory=default_ollama_base_url)
    model: str = "llama3.2"


class OpenRouterSettings(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    model: str = "openai/gpt-4o-mini"


class GigaChatSettings(BaseModel):
    credentials: str = ""
    scope: str = "GIGACHAT_API_PERS"
    base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    model: str = "GigaChat"
    verify_ssl: bool = True


class LlmConfig(BaseModel):
    provider: TextLlmProvider = TextLlmProvider.ollama
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    gigachat: GigaChatSettings = Field(default_factory=GigaChatSettings)


def mask_secret(value: str | None, *, keep: int = 4) -> str | None:
    if not value:
        return None
    if len(value) <= keep:
        return "•" * len(value)
    return "•" * max(8, len(value) - keep) + value[-keep:]


class LlmConfigStore:
    """Load / save LLM config from ``data_dir/llm_config.json``."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> LlmConfig:
        if not self.path.is_file():
            return LlmConfig()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return LlmConfig()
        return LlmConfig.model_validate(raw)

    def save(self, config: LlmConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="json")
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def merge_update(self, patch: dict[str, Any]) -> LlmConfig:
        """Apply a partial update; blank secrets keep previously stored values."""
        current = self.load()
        data = current.model_dump(mode="json")

        if "provider" in patch and patch["provider"] is not None:
            data["provider"] = patch["provider"]

        for key in ("ollama", "openrouter", "gigachat"):
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

        updated = LlmConfig.model_validate(data)
        self.save(updated)
        return updated

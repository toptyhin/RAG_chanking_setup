"""Persisted text-LLM connection settings (JSON under DATA_DIR)."""

from __future__ import annotations

import json
import logging
import os
import uuid
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON via a temp file + ``os.replace`` so readers never see a half file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class LlmConfigStore:
    """Load / save LLM config from ``data_dir/llm_config.json``."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> LlmConfig:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return LlmConfig()
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            # A concurrent non-atomic writer (older builds) could leave the file
            # empty/truncated; fall back to defaults instead of a 500 response.
            logger.warning(
                "invalid JSON in %s (%s); using defaults", self.path, exc
            )
            return LlmConfig()
        if not isinstance(raw, dict):
            logger.warning("%s is not a JSON object; using defaults", self.path)
            return LlmConfig()
        return LlmConfig.model_validate(raw)

    def save(self, config: LlmConfig) -> None:
        payload = config.model_dump(mode="json")
        write_json_atomic(self.path, payload)

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

"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for local Docker MVP."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("./data"), validation_alias="DATA_DIR")
    sqlite_url: str = Field(
        default="sqlite+aiosqlite:///./data/rageval.db",
        validation_alias="SQLITE_URL",
    )
    qdrant_url: str = Field(
        default="http://localhost:6333",
        validation_alias="QDRANT_URL",
    )
    embedding_provider: str = Field(
        default="hash",
        validation_alias="EMBEDDING_PROVIDER",
    )  # hash | sentence_transformers
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL",
    )
    rerank_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias="RERANK_MODEL",
    )
    hf_token: str | None = Field(default=None, validation_alias="HF_TOKEN")

    @field_validator("data_dir", mode="before")
    @classmethod
    def _coerce_data_dir(cls, value: object) -> Path:
        return Path(str(value)).expanduser()

    @field_validator("hf_token", mode="before")
    @classmethod
    def _empty_hf_token(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @property
    def objects_dir(self) -> Path:
        return self.data_dir / "objects"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (clear via `get_settings.cache_clear()` in tests)."""
    return Settings()

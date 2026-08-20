"""Embedding provider config + connection test."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from rageval_embedding_providers import (
    EmbeddingConfig,
    EmbeddingConfigStore,
    EmbeddingProviderKind,
    list_model_infos,
    mask_secret,
    test_connection,
)
from rageval_llm_providers import LlmConfigStore
from rageval_llm_providers.catalog import ModelPurpose, RemoteModelInfo
from rageval_api.services.shared_provider_connections import (
    heal_shared_provider_secrets,
    sync_shared_provider_connections,
)

router = APIRouter(prefix="/embedding", tags=["embedding"])


class SentenceTransformersSettingsIn(BaseModel):
    model: str | None = None


class OllamaSettingsIn(BaseModel):
    base_url: str | None = None
    model: str | None = None


class OpenRouterSettingsIn(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class GigaChatSettingsIn(BaseModel):
    credentials: str | None = None
    scope: str | None = None
    base_url: str | None = None
    auth_url: str | None = None
    model: str | None = None
    verify_ssl: bool | None = None


class EmbeddingConfigUpdate(BaseModel):
    provider: EmbeddingProviderKind | None = None
    sentence_transformers: SentenceTransformersSettingsIn | None = None
    ollama: OllamaSettingsIn | None = None
    openrouter: OpenRouterSettingsIn | None = None
    gigachat: GigaChatSettingsIn | None = None


class SentenceTransformersSettingsOut(BaseModel):
    model: str


class OllamaSettingsOut(BaseModel):
    base_url: str
    model: str


class OpenRouterSettingsOut(BaseModel):
    base_url: str
    model: str
    api_key_configured: bool
    api_key_masked: str | None = None


class GigaChatSettingsOut(BaseModel):
    scope: str
    base_url: str
    auth_url: str
    model: str
    verify_ssl: bool
    credentials_configured: bool
    credentials_masked: str | None = None


class EmbeddingConfigOut(BaseModel):
    provider: EmbeddingProviderKind
    sentence_transformers: SentenceTransformersSettingsOut
    ollama: OllamaSettingsOut
    openrouter: OpenRouterSettingsOut
    gigachat: GigaChatSettingsOut


class ConnectionTestOut(BaseModel):
    ok: bool
    latency_ms: float
    message: str
    provider: EmbeddingProviderKind
    model: str | None = None
    models: list[str] = Field(default_factory=list)


class EmbeddingModelsOut(BaseModel):
    ok: bool
    provider: EmbeddingProviderKind
    models: list[str] = Field(default_factory=list)
    items: list[RemoteModelInfo] = Field(default_factory=list)
    message: str | None = None


def _store(request: Request) -> EmbeddingConfigStore:
    store = getattr(request.app.state, "embedding_config_store", None)
    if store is None:
        settings = request.app.state.settings
        path = Path(settings.data_dir) / "embedding_config.json"
        store = EmbeddingConfigStore(path)
        request.app.state.embedding_config_store = store
    return store


def _llm_store(request: Request) -> LlmConfigStore:
    store = getattr(request.app.state, "llm_config_store", None)
    if store is None:
        settings = request.app.state.settings
        path = Path(settings.data_dir) / "llm_config.json"
        store = LlmConfigStore(path)
        request.app.state.llm_config_store = store
    return store


def _merge_config(saved: EmbeddingConfig, body: EmbeddingConfigUpdate | None) -> EmbeddingConfig:
    if body is None:
        return saved
    patch = body.model_dump(exclude_unset=True)
    data = saved.model_dump(mode="json")
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
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    continue
            if value is not None:
                merged[field] = value
        data[key] = merged
    return EmbeddingConfig.model_validate(data)


def _to_out(config: EmbeddingConfig) -> EmbeddingConfigOut:
    return EmbeddingConfigOut(
        provider=config.provider,
        sentence_transformers=SentenceTransformersSettingsOut(
            model=config.sentence_transformers.model,
        ),
        ollama=OllamaSettingsOut(
            base_url=config.ollama.base_url,
            model=config.ollama.model,
        ),
        openrouter=OpenRouterSettingsOut(
            base_url=config.openrouter.base_url,
            model=config.openrouter.model,
            api_key_configured=bool(config.openrouter.api_key.strip()),
            api_key_masked=mask_secret(config.openrouter.api_key),
        ),
        gigachat=GigaChatSettingsOut(
            scope=config.gigachat.scope,
            base_url=config.gigachat.base_url,
            auth_url=config.gigachat.auth_url,
            model=config.gigachat.model,
            verify_ssl=config.gigachat.verify_ssl,
            credentials_configured=bool(config.gigachat.credentials.strip()),
            credentials_masked=mask_secret(config.gigachat.credentials),
        ),
    )


@router.get("/config", response_model=EmbeddingConfigOut)
def get_embedding_config(request: Request) -> EmbeddingConfigOut:
    _llm, emb = heal_shared_provider_secrets(_llm_store(request), _store(request))
    return _to_out(emb)


@router.put("/config", response_model=EmbeddingConfigOut)
def put_embedding_config(body: EmbeddingConfigUpdate, request: Request) -> EmbeddingConfigOut:
    store = _store(request)
    patch: dict[str, Any] = body.model_dump(exclude_unset=True)
    store.merge_update(patch)
    _llm, updated = sync_shared_provider_connections(
        _llm_store(request), store, prefer="embedding"
    )
    return _to_out(updated)


@router.post("/test", response_model=ConnectionTestOut)
def post_embedding_test(
    request: Request,
    body: EmbeddingConfigUpdate | None = None,
) -> ConnectionTestOut:
    """Test connection using saved config, optionally overridden by request body."""
    _llm, emb = heal_shared_provider_secrets(_llm_store(request), _store(request))
    config = _merge_config(emb, body)
    result = test_connection(config)
    return ConnectionTestOut(
        ok=result.ok,
        latency_ms=result.latency_ms,
        message=result.message,
        provider=config.provider,
        model=result.model,
        models=list(result.models or []),
    )


@router.post("/models", response_model=EmbeddingModelsOut)
def post_embedding_models(
    request: Request,
    body: EmbeddingConfigUpdate | None = None,
) -> EmbeddingModelsOut:
    """List models for the (optionally overridden) provider config."""
    _llm, emb = heal_shared_provider_secrets(_llm_store(request), _store(request))
    config = _merge_config(emb, body)
    try:
        items = list_model_infos(config, purpose=ModelPurpose.embeddings)
    except Exception as exc:  # noqa: BLE001
        return EmbeddingModelsOut(
            ok=False,
            provider=config.provider,
            models=[],
            items=[],
            message=str(exc),
        )
    return EmbeddingModelsOut(
        ok=True,
        provider=config.provider,
        models=[m.id for m in items],
        items=items,
        message=None,
    )


@router.get("/models", response_model=EmbeddingModelsOut)
def get_embedding_models(request: Request) -> EmbeddingModelsOut:
    return post_embedding_models(request, body=None)

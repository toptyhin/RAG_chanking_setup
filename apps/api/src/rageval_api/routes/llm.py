"""Text LLM provider config + connection test."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from rageval_embedding_providers import EmbeddingConfigStore
from rageval_llm_providers import (
    LlmConfig,
    LlmConfigStore,
    TextLlmProvider,
    mask_secret,
    test_connection,
)
from rageval_llm_providers.catalog import ModelPurpose, RemoteModelInfo
from rageval_llm_providers.factory import list_model_infos
from rageval_api.services.shared_provider_connections import (
    heal_shared_provider_secrets,
    save_llm_config,
)

router = APIRouter(prefix="/llm", tags=["llm"])

ModelPurposeIn = Literal["text", "embeddings", "rerank"]


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


class LlmConfigUpdate(BaseModel):
    provider: TextLlmProvider | None = None
    ollama: OllamaSettingsIn | None = None
    openrouter: OpenRouterSettingsIn | None = None
    gigachat: GigaChatSettingsIn | None = None
    # Only used by /models — ignored by config merge.
    purpose: ModelPurposeIn | None = None


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


class LlmConfigOut(BaseModel):
    provider: TextLlmProvider
    ollama: OllamaSettingsOut
    openrouter: OpenRouterSettingsOut
    gigachat: GigaChatSettingsOut


class ConnectionTestOut(BaseModel):
    ok: bool
    latency_ms: float
    message: str
    provider: TextLlmProvider
    model: str | None = None
    models: list[str] = Field(default_factory=list)


class LlmModelsOut(BaseModel):
    ok: bool
    provider: TextLlmProvider
    models: list[str] = Field(default_factory=list)
    items: list[RemoteModelInfo] = Field(default_factory=list)
    message: str | None = None


def _store(request: Request) -> LlmConfigStore:
    store = getattr(request.app.state, "llm_config_store", None)
    if store is None:
        settings = request.app.state.settings
        path = Path(settings.data_dir) / "llm_config.json"
        store = LlmConfigStore(path)
        request.app.state.llm_config_store = store
    return store


def _embedding_store(request: Request) -> EmbeddingConfigStore:
    store = getattr(request.app.state, "embedding_config_store", None)
    if store is None:
        settings = request.app.state.settings
        path = Path(settings.data_dir) / "embedding_config.json"
        store = EmbeddingConfigStore(path)
        request.app.state.embedding_config_store = store
    return store


def _merge_config(saved: LlmConfig, body: LlmConfigUpdate | None) -> LlmConfig:
    if body is None:
        return saved
    patch = body.model_dump(exclude_unset=True, exclude={"purpose"})
    data = saved.model_dump(mode="json")
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
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    continue
            if value is not None:
                merged[field] = value
        data[key] = merged
    return LlmConfig.model_validate(data)


def _purpose_from_body(body: LlmConfigUpdate | None) -> ModelPurpose:
    if body is None or body.purpose is None:
        return ModelPurpose.text
    return ModelPurpose(body.purpose)


def _to_out(config: LlmConfig) -> LlmConfigOut:
    return LlmConfigOut(
        provider=config.provider,
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


@router.get("/config", response_model=LlmConfigOut)
def get_llm_config(request: Request) -> LlmConfigOut:
    llm, _emb = heal_shared_provider_secrets(_store(request), _embedding_store(request))
    return _to_out(llm)


@router.put("/config", response_model=LlmConfigOut)
def put_llm_config(body: LlmConfigUpdate, request: Request) -> LlmConfigOut:
    patch: dict[str, Any] = body.model_dump(exclude_unset=True, exclude={"purpose"})
    updated, _emb = save_llm_config(
        _store(request), _embedding_store(request), patch
    )
    return _to_out(updated)


@router.post("/test", response_model=ConnectionTestOut)
def post_llm_test(
    request: Request,
    body: LlmConfigUpdate | None = None,
) -> ConnectionTestOut:
    """Test connection using saved config, optionally overridden by request body."""
    llm, _emb = heal_shared_provider_secrets(_store(request), _embedding_store(request))
    config = _merge_config(llm, body)
    result = test_connection(config)
    return ConnectionTestOut(
        ok=result.ok,
        latency_ms=result.latency_ms,
        message=result.message,
        provider=config.provider,
        model=result.model,
        models=list(result.models or []),
    )


@router.post("/models", response_model=LlmModelsOut)
def post_llm_models(
    request: Request,
    body: LlmConfigUpdate | None = None,
) -> LlmModelsOut:
    """List models for the (optionally overridden) provider config."""
    llm, _emb = heal_shared_provider_secrets(_store(request), _embedding_store(request))
    config = _merge_config(llm, body)
    purpose = _purpose_from_body(body)
    try:
        items = list_model_infos(config, purpose=purpose)
    except Exception as exc:  # noqa: BLE001
        return LlmModelsOut(
            ok=False,
            provider=config.provider,
            models=[],
            items=[],
            message=str(exc),
        )
    return LlmModelsOut(
        ok=True,
        provider=config.provider,
        models=[m.id for m in items],
        items=items,
        message=None,
    )


@router.get("/models", response_model=LlmModelsOut)
def get_llm_models(request: Request) -> LlmModelsOut:
    return post_llm_models(request, body=None)

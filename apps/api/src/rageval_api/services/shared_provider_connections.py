"""Keep OpenRouter / Ollama / GigaChat connection settings identical across stores.

LLM and embedding configs are separate JSON files (models differ), but API keys,
credentials, and base URLs must stay shared so connection tabs do not diverge.
"""

from __future__ import annotations

from typing import Literal

from rageval_embedding_providers import EmbeddingConfig, EmbeddingConfigStore
from rageval_llm_providers import LlmConfig, LlmConfigStore

Prefer = Literal["llm", "embedding"]


def _nonempty(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _pick_secret(preferred: str, other: str) -> str:
    return _nonempty(preferred) or _nonempty(other) or ""


def sync_shared_provider_connections(
    llm_store: LlmConfigStore,
    embedding_store: EmbeddingConfigStore,
    *,
    prefer: Prefer,
) -> tuple[LlmConfig, EmbeddingConfig]:
    """Unify shared connection fields; ``prefer`` wins for non-secret URLs/flags."""
    llm = llm_store.load()
    emb = embedding_store.load()

    if prefer == "llm":
        ollama_base = llm.ollama.base_url
        openrouter_base = llm.openrouter.base_url
        gigachat_scope = llm.gigachat.scope
        gigachat_base = llm.gigachat.base_url
        gigachat_auth = llm.gigachat.auth_url
        gigachat_verify = llm.gigachat.verify_ssl
        openrouter_key = _pick_secret(llm.openrouter.api_key, emb.openrouter.api_key)
        gigachat_creds = _pick_secret(llm.gigachat.credentials, emb.gigachat.credentials)
    else:
        ollama_base = emb.ollama.base_url
        openrouter_base = emb.openrouter.base_url
        gigachat_scope = emb.gigachat.scope
        gigachat_base = emb.gigachat.base_url
        gigachat_auth = emb.gigachat.auth_url
        gigachat_verify = emb.gigachat.verify_ssl
        openrouter_key = _pick_secret(emb.openrouter.api_key, llm.openrouter.api_key)
        gigachat_creds = _pick_secret(emb.gigachat.credentials, llm.gigachat.credentials)

    patch = {
        "ollama": {"base_url": ollama_base},
        "openrouter": {"base_url": openrouter_base, "api_key": openrouter_key},
        "gigachat": {
            "credentials": gigachat_creds,
            "scope": gigachat_scope,
            "base_url": gigachat_base,
            "auth_url": gigachat_auth,
            "verify_ssl": gigachat_verify,
        },
    }
    return llm_store.merge_update(patch), embedding_store.merge_update(patch)


def heal_shared_provider_secrets(
    llm_store: LlmConfigStore,
    embedding_store: EmbeddingConfigStore,
) -> tuple[LlmConfig, EmbeddingConfig]:
    """Copy missing secrets / drifted URLs so both stores share one connection."""
    llm = llm_store.load()
    emb = embedding_store.load()

    identical = (
        llm.ollama.base_url == emb.ollama.base_url
        and llm.openrouter.base_url == emb.openrouter.base_url
        and llm.openrouter.api_key == emb.openrouter.api_key
        and llm.gigachat.base_url == emb.gigachat.base_url
        and llm.gigachat.auth_url == emb.gigachat.auth_url
        and llm.gigachat.scope == emb.gigachat.scope
        and llm.gigachat.verify_ssl == emb.gigachat.verify_ssl
        and llm.gigachat.credentials == emb.gigachat.credentials
    )
    if identical:
        return llm, emb

    prefer: Prefer = "llm"
    if _nonempty(emb.openrouter.api_key) and not _nonempty(llm.openrouter.api_key):
        prefer = "embedding"
    elif _nonempty(emb.gigachat.credentials) and not _nonempty(llm.gigachat.credentials):
        prefer = "embedding"

    return sync_shared_provider_connections(
        llm_store, embedding_store, prefer=prefer
    )

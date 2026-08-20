"""Lazy chunker registry."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from rageval_domain import ChunkSet, CleanCorpus

from rageval_chunking.options import (
    PROVIDER_LABELS,
    PROVIDER_MODES,
    PROVIDER_OPTION_MODELS,
    PROVIDER_ORDER,
    ChunkerOptions,
    parse_chunker_options,
)
from rageval_chunking.protocol import Chunker

# provider -> (module path, class name, optional third-party package for availability)
_ADAPTER_SPECS: dict[str, tuple[str, str, str | None]] = {
    "semchunk": (
        "rageval_chunking.adapters.semchunk_adapter",
        "SemchunkChunker",
        "semchunk",
    ),
    "chunklet": (
        "rageval_chunking.adapters.chunklet_adapter",
        "ChunkletChunker",
        "chunklet",
    ),
    "reference_fixed": (
        "rageval_chunking.adapters.reference_adapter",
        "ReferenceChunker",
        None,
    ),
}

_instances: dict[str, Chunker] = {}


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    label: str
    modes: list[str]
    available: bool
    options_schema: dict[str, Any]
    unavailable_reason: str | None = None


def _probe_package(package: str | None) -> tuple[bool, str | None]:
    if package is None:
        return True, None
    try:
        importlib.import_module(package)
    except ImportError as exc:
        return False, f"optional package {package!r} is not installed: {exc}"
    return True, None


def _probe_adapter_module(module_path: str) -> tuple[bool, str | None]:
    try:
        importlib.import_module(module_path)
    except ImportError as exc:
        return False, f"adapter not available: {exc}"
    return True, None


def is_provider_available(provider: str) -> tuple[bool, str | None]:
    if provider not in _ADAPTER_SPECS:
        return False, f"unknown provider: {provider}"
    module_path, _, package = _ADAPTER_SPECS[provider]
    # Probe third-party package first (avoids importing heavy adapter deps unnecessarily
    # beyond what the package itself needs).
    ok, reason = _probe_package(package)
    if not ok:
        return False, reason
    return _probe_adapter_module(module_path)


def list_providers() -> list[ProviderInfo]:
    result: list[ProviderInfo] = []
    for provider_id in PROVIDER_ORDER:
        model = PROVIDER_OPTION_MODELS[provider_id]
        available, reason = is_provider_available(provider_id)
        result.append(
            ProviderInfo(
                id=provider_id,
                label=PROVIDER_LABELS[provider_id],
                modes=list(PROVIDER_MODES.get(provider_id, [])),
                available=available,
                options_schema=model.model_json_schema(),
                unavailable_reason=None if available else reason,
            )
        )
    return result


def ensure_provider(provider: str) -> Chunker:
    """Import and cache a chunker instance (lazy third-party import)."""
    if provider in _instances:
        return _instances[provider]
    if provider not in _ADAPTER_SPECS:
        raise ValueError(f"unknown chunker provider: {provider}")

    available, reason = is_provider_available(provider)
    if not available:
        raise ImportError(reason or f"provider {provider} is unavailable")

    module_path, class_name, _ = _ADAPTER_SPECS[provider]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    instance: Chunker = cls()
    _instances[provider] = instance
    return instance


def get_chunker(provider: str) -> Chunker:
    return ensure_provider(provider)


def chunk_corpus(
    corpus: CleanCorpus,
    options: ChunkerOptions | dict[str, Any],
) -> ChunkSet:
    """Chunk a clean corpus with the selected provider options."""
    if isinstance(options, dict):
        parsed = parse_chunker_options(options)
    else:
        parsed = options
    chunker = ensure_provider(parsed.provider)
    return chunker.chunk_corpus(corpus, parsed)


def clear_registry_cache() -> None:
    """Drop cached chunker instances (tests)."""
    _instances.clear()

"""Remote model catalog entries (OpenRouter / GigaChat / Ollama)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelPurpose(str, Enum):
    """Which product surface the catalog is for."""

    text = "text"
    embeddings = "embeddings"
    rerank = "rerank"


class RemoteModelInfo(BaseModel):
    id: str
    name: str
    context_length: int | None = None
    modality: str | None = None
    input_modalities: list[str] = Field(default_factory=list)
    output_modalities: list[str] = Field(default_factory=list)
    # OpenRouter Models API: which chat/completions params the model advertises.
    supported_parameters: list[str] = Field(default_factory=list)
    # Native / default embedding size when known.
    dimension: int | None = None
    # MRL (Matryoshka) sizes when the model advertises multiple usable dims.
    # Empty means unknown or fixed single dim (see ``dimension``).
    dimensions: list[int] = Field(default_factory=list)


# Public GigaChat context windows (approximate; API does not expose them).
_GIGACHAT_CONTEXT: dict[str, int] = {
    "gigachat": 128_000,
    "gigachat-2": 128_000,
    "gigachat-2-pro": 128_000,
    "gigachat-2-max": 128_000,
    "gigachat-pro": 128_000,
    "gigachat-max": 128_000,
    "gigachat-plus": 128_000,
    "embeddings": 2_048,
    "embeddings-2": 4_096,
    "embeddingsgigar": 4_096,
}

# Native embedding dims for GigaChat embedding models.
_GIGACHAT_EMBED_DIM: dict[str, int] = {
    "embeddings": 1024,
    "embeddings-2": 1024,
    "embeddingsgigar": 1024,
}

# Known native dim + optional MRL sizes (includes native). Keys matched as
# lowercase id equality or suffix after stripping tags (``:latest`` / ``:free``).
# MRL lists are common presets, not always every legal truncate size.
_KNOWN_EMBED_DIMS: dict[str, tuple[int, list[int]]] = {
    "openai/text-embedding-3-small": (1536, [512, 1536]),
    "openai/text-embedding-3-large": (3072, [256, 1024, 3072]),
    "openai/text-embedding-ada-002": (1536, []),
    "qwen/qwen3-embedding-0.6b": (1024, [256, 512, 1024]),
    "qwen/qwen3-embedding-4b": (2560, [512, 1024, 2560]),
    "qwen/qwen3-embedding-8b": (4096, [512, 1024, 2048, 4096]),
    "nomic-embed-text": (768, [64, 128, 256, 512, 768]),
    "nomic-embed-text-v1.5": (768, [64, 128, 256, 512, 768]),
    "nomic-ai/nomic-embed-text-v1.5": (768, [64, 128, 256, 512, 768]),
    "mistralai/mistral-embed-2312": (1024, []),
    "mistralai/codestral-embed-2505": (1024, []),
    "thenlper/gte-base": (768, []),
    "thenlper/gte-large": (1024, []),
    "intfloat/e5-base-v2": (768, []),
    "intfloat/e5-large-v2": (1024, []),
    "intfloat/multilingual-e5-large": (1024, []),
    "baai/bge-base-en-v1.5": (768, []),
    "baai/bge-large-en-v1.5": (1024, []),
    "baai/bge-m3": (1024, []),
    "sentence-transformers/all-minilm-l6-v2": (384, []),
    "sentence-transformers/all-minilm-l12-v2": (384, []),
    "sentence-transformers/all-mpnet-base-v2": (768, []),
    "sentence-transformers/paraphrase-minilm-l6-v2": (384, []),
    "sentence-transformers/multi-qa-mpnet-base-dot-v1": (768, []),
    "google/gemini-embedding-001": (3072, [768, 1536, 3072]),
    "embeddings": (1024, []),
    "embeddings-2": (1024, []),
    "embeddingsgigar": (1024, []),
}

_DIM_IN_DESC_RE = re.compile(
    r"(\d{2,5})\s*-\s*dimensional|\binto\s+a?\s*(\d{2,5})\s*-?\s*dim",
    re.IGNORECASE,
)


def _strip_model_tag(model_id: str) -> str:
    """``nomic-embed-text:latest`` → ``nomic-embed-text``; keep HF/OR slashes."""
    mid = model_id.strip().lower()
    if ":" in mid and "/" not in mid.split(":")[0]:
        # ollama-style tag
        return mid.split(":", 1)[0]
    if mid.endswith(":free"):
        return mid[: -len(":free")]
    return mid


def lookup_known_embedding_dims(model_id: str) -> tuple[int | None, list[int]]:
    """Return (native_dim, mrl_dims) from the static table."""
    mid = _strip_model_tag(model_id)
    if mid in _KNOWN_EMBED_DIMS:
        native, dims = _KNOWN_EMBED_DIMS[mid]
        return native, list(dims)
    # Match by suffix (``openai/text-embedding-3-small`` vs bare name).
    for key, (native, dims) in _KNOWN_EMBED_DIMS.items():
        if mid == key or mid.endswith("/" + key) or key.endswith("/" + mid):
            return native, list(dims)
        if "/" not in key and (mid == key or mid.endswith("/" + key)):
            return native, list(dims)
    return None, []


def parse_dimension_from_description(description: str | None) -> int | None:
    if not description:
        return None
    match = _DIM_IN_DESC_RE.search(description)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if 16 <= value <= 16_384 else None


def resolve_embedding_dimensions(
    model_id: str,
    *,
    description: str | None = None,
    probed: int | None = None,
) -> tuple[int | None, list[int]]:
    """Merge known table, description parse, and optional probe into dim fields."""
    native, mrl = lookup_known_embedding_dims(model_id)
    if native is None:
        native = parse_dimension_from_description(description)
    if probed is not None and probed > 0:
        if native is None:
            native = probed
        elif probed != native and not mrl:
            # Prefer live probe over stale table for fixed-dim models.
            native = probed
    if mrl and native is not None and native not in mrl:
        mrl = sorted({*mrl, native})
    return native, mrl


def _format_modality(inputs: list[str], outputs: list[str]) -> str | None:
    if not inputs and not outputs:
        return None
    left = "+".join(inputs) if inputs else "?"
    right = "+".join(outputs) if outputs else "?"
    return f"{left}\u2192{right}"


def parse_openrouter_model(item: dict[str, Any]) -> RemoteModelInfo | None:
    mid = item.get("id")
    if not isinstance(mid, str) or not mid.strip():
        return None
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        name = mid
    context_length = _openrouter_context_length(item)
    inputs, outputs, modality = _openrouter_modalities(item)
    supported_parameters = _openrouter_supported_params(item)
    description = item.get("description") if isinstance(item.get("description"), str) else None
    is_embedding = "embeddings" in outputs or "embed" in mid.lower()
    dimension: int | None = None
    dimensions: list[int] = []
    if is_embedding:
        dimension, dimensions = resolve_embedding_dimensions(
            mid.strip(), description=description
        )
    return RemoteModelInfo(
        id=mid.strip(),
        name=name.strip(),
        context_length=context_length,
        modality=modality,
        input_modalities=inputs,
        output_modalities=outputs,
        supported_parameters=supported_parameters,
        dimension=dimension,
        dimensions=dimensions,
    )


def _openrouter_context_length(item: dict[str, Any]) -> int | None:
    ctx = item.get("context_length")
    if not isinstance(ctx, (int, float)) or ctx <= 0:
        top = item.get("top_provider")
        if isinstance(top, dict):
            ctx = top.get("context_length")
    if isinstance(ctx, (int, float)) and ctx > 0:
        return int(ctx)
    return None


def _openrouter_modalities(
    item: dict[str, Any],
) -> tuple[list[str], list[str], str | None]:
    arch = item.get("architecture") if isinstance(item.get("architecture"), dict) else {}
    inputs = [
        str(x) for x in (arch.get("input_modalities") or []) if isinstance(x, str) and x
    ]
    outputs = [
        str(x) for x in (arch.get("output_modalities") or []) if isinstance(x, str) and x
    ]
    modality = arch.get("modality") if isinstance(arch.get("modality"), str) else None
    if not modality:
        modality = _format_modality(inputs, outputs)
    return inputs, outputs, modality


def _openrouter_supported_params(item: dict[str, Any]) -> list[str]:
    supported_raw = item.get("supported_parameters")
    supported_parameters: list[str] = []
    if not isinstance(supported_raw, list):
        return supported_parameters
    seen: set[str] = set()
    for raw in supported_raw:
        if not isinstance(raw, str):
            continue
        param = raw.strip()
        if not param or param in seen:
            continue
        seen.add(param)
        supported_parameters.append(param)
    return supported_parameters


def openrouter_output_modality_param(purpose: ModelPurpose) -> str:
    if purpose == ModelPurpose.embeddings:
        return "embeddings"
    if purpose == ModelPurpose.rerank:
        return "rerank"
    return "text"


def filter_openrouter_models(
    items: list[RemoteModelInfo],
    *,
    purpose: ModelPurpose,
) -> list[RemoteModelInfo]:
    """Client-side safety filter when upstream ignored output_modalities."""
    if purpose == ModelPurpose.embeddings:
        return [
            m
            for m in items
            if "embeddings" in m.output_modalities
            or "embed" in m.id.lower()
            or "embed" in m.name.lower()
        ]
    if purpose == ModelPurpose.rerank:
        return [
            m
            for m in items
            if "rerank" in m.output_modalities
            or "rerank" in m.id.lower()
            or "rerank" in m.name.lower()
        ]
    # text: exclude pure embedding / rerank catalogs
    return [
        m
        for m in items
        if "embeddings" not in m.output_modalities
        and "rerank" not in m.output_modalities
        and "embed" not in m.id.lower()
    ]


def _gigachat_is_embedding(model_id: str) -> bool:
    low = model_id.lower()
    return "embed" in low


def _gigachat_is_rerank(model_id: str) -> bool:
    low = model_id.lower()
    return "rerank" in low or "ranker" in low


def parse_gigachat_model(item: dict[str, Any] | str) -> RemoteModelInfo | None:
    if isinstance(item, str):
        mid = item.strip()
    elif isinstance(item, dict):
        raw = item.get("id") or item.get("name")
        mid = raw.strip() if isinstance(raw, str) else ""
    else:
        mid = ""
    if not mid:
        return None

    low = mid.lower()
    context_length = _GIGACHAT_CONTEXT.get(low)
    dimension: int | None = None
    dimensions: list[int] = []
    if _gigachat_is_embedding(mid):
        modality = "text\u2192embeddings"
        outputs = ["embeddings"]
        inputs = ["text"]
        dimension = _GIGACHAT_EMBED_DIM.get(low)
        if dimension is None:
            dimension, dimensions = resolve_embedding_dimensions(mid)
        else:
            _, dimensions = resolve_embedding_dimensions(mid)
    elif _gigachat_is_rerank(mid):
        modality = "text\u2192rerank"
        outputs = ["rerank"]
        inputs = ["text"]
    else:
        modality = "text\u2192text"
        outputs = ["text"]
        inputs = ["text"]

    return RemoteModelInfo(
        id=mid,
        name=mid,
        context_length=context_length,
        modality=modality,
        input_modalities=inputs,
        output_modalities=outputs,
        dimension=dimension,
        dimensions=dimensions,
    )


def filter_gigachat_models(
    items: list[RemoteModelInfo],
    *,
    purpose: ModelPurpose,
) -> list[RemoteModelInfo]:
    if purpose == ModelPurpose.embeddings:
        return [m for m in items if _gigachat_is_embedding(m.id)]
    if purpose == ModelPurpose.rerank:
        return [m for m in items if _gigachat_is_rerank(m.id)]
    return [
        m
        for m in items
        if not _gigachat_is_embedding(m.id) and not _gigachat_is_rerank(m.id)
    ]


def ollama_model_infos(
    names: list[str],
    *,
    dimensions_by_id: dict[str, int] | None = None,
) -> list[RemoteModelInfo]:
    dims_map = dimensions_by_id or {}
    out: list[RemoteModelInfo] = []
    for name in names:
        if not name.strip():
            continue
        probed = dims_map.get(name) or dims_map.get(_strip_model_tag(name))
        native, mrl = resolve_embedding_dimensions(name, probed=probed)
        out.append(
            RemoteModelInfo(
                id=name,
                name=name,
                context_length=None,
                modality=None,
                dimension=native,
                dimensions=mrl,
            )
        )
    return out

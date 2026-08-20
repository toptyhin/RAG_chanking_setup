"""Hugging Face Hub model catalog (HTTP proxy, no ML deps)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Literal

import httpx

HF_API = "https://huggingface.co/api/models"

ModelKind = Literal["embedding", "rerank"]


@dataclass(slots=True, frozen=True)
class HubModelInfo:
    id: str
    downloads: int
    likes: int
    pipeline_tag: str | None
    tags: list[str]
    library_name: str | None
    size_bytes: int | None = None


class HfHubCatalog:
    """Search and validate models on the Hugging Face Hub via REST."""

    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str = HF_API,
        timeout: float = 30.0,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def search(
        self,
        kind: ModelKind,
        *,
        query: str = "",
        limit: int = 20,
    ) -> list[HubModelInfo]:
        limit = max(1, min(int(limit), 50))
        # Oversample — Hub `filter=sentence-transformers` is noisy (GGUF/MLX mirrors).
        fetch_limit = min(100, max(limit * 4, limit))
        params: dict[str, Any] = {
            "limit": fetch_limit,
            "sort": "downloads",
            "direction": -1,
            "filter": "sentence-transformers",
        }
        if kind == "embedding":
            params["pipeline_tag"] = "feature-extraction"
            if query.strip():
                params["search"] = query.strip()
        else:
            params["search"] = query.strip() or "cross-encoder"

        with httpx.Client(timeout=self._timeout, headers=self._headers()) as client:
            response = client.get(self._base_url, params=params)
            response.raise_for_status()
            raw = response.json()

        items = [_parse_model(row) for row in raw if isinstance(row, dict)]
        if kind == "embedding":
            items = [m for m in items if _is_st_embedding(m)]
        else:
            items = [m for m in items if _is_st_rerank(m)]
        return items[:limit]

    def get_model(self, model_id: str) -> HubModelInfo | None:
        """Full model card fields (library/tags/pipeline). Do not use expand-only."""
        model_id = model_id.strip()
        if not model_id or "/" not in model_id:
            return None
        url = f"{self._base_url}/{model_id}"
        with httpx.Client(timeout=self._timeout, headers=self._headers()) as client:
            response = client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            return None
        return _parse_model(data)

    def get_used_storage(self, model_id: str) -> int | None:
        """Return approximate on-disk bytes for a full Hub snapshot, or None."""
        model_id = model_id.strip()
        if not model_id or "/" not in model_id:
            return None
        url = f"{self._base_url}/{model_id}"
        with httpx.Client(timeout=self._timeout, headers=self._headers()) as client:
            # Single expand value — comma lists are rejected by the Hub API.
            response = client.get(url, params={"expand": "usedStorage"})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            return None
        return _extract_size_bytes(data)

    def get_used_storage_many(
        self,
        model_ids: list[str],
        *,
        max_workers: int = 8,
    ) -> dict[str, int | None]:
        """Fetch usedStorage for many ids (bounded parallelism)."""
        unique: list[str] = []
        seen: set[str] = set()
        for mid in model_ids:
            mid = mid.strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            unique.append(mid)
        if not unique:
            return {}

        result: dict[str, int | None] = {mid: None for mid in unique}
        workers = max(1, min(max_workers, len(unique)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.get_used_storage, mid): mid for mid in unique}
            for fut in as_completed(futures):
                mid = futures[fut]
                try:
                    result[mid] = fut.result()
                except Exception:  # noqa: BLE001
                    result[mid] = None
        return result

    def validate_for_kind(self, kind: ModelKind, model_id: str) -> HubModelInfo:
        """Ensure model exists and is a sentence-transformers model for kind."""
        info = self.get_model(model_id)
        if info is None:
            raise LookupError(f"model not found on Hugging Face Hub: {model_id}")
        if kind == "embedding":
            if not _is_st_embedding(info):
                raise ValueError(
                    f"model {model_id} is not a sentence-transformers embedding model"
                )
            return info
        if not _is_st_rerank(info):
            raise ValueError(
                f"model {model_id} is not a sentence-transformers cross-encoder"
            )
        return info


def _parse_model(row: dict[str, Any]) -> HubModelInfo:
    model_id = str(row.get("id") or row.get("modelId") or "")
    tags_raw = row.get("tags") or []
    tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
    pipeline = row.get("pipeline_tag")
    library = row.get("library_name")
    return HubModelInfo(
        id=model_id,
        downloads=int(row.get("downloads") or 0),
        likes=int(row.get("likes") or 0),
        pipeline_tag=str(pipeline) if pipeline else None,
        tags=tags,
        library_name=str(library) if library else None,
        size_bytes=_extract_size_bytes(row),
    )


def _extract_size_bytes(row: dict[str, Any]) -> int | None:
    """Prefer usedStorage; fall back to sum of sibling file sizes."""
    used = row.get("usedStorage")
    if used is None:
        used = row.get("used_storage")
    if isinstance(used, (int, float)) and used >= 0:
        return int(used)

    siblings = row.get("siblings")
    if not isinstance(siblings, list):
        return None
    total = 0
    found = False
    for sib in siblings:
        if not isinstance(sib, dict):
            continue
        size = sib.get("size")
        if size is None and isinstance(sib.get("lfs"), dict):
            size = sib["lfs"].get("size")
        if isinstance(size, (int, float)) and size >= 0:
            total += int(size)
            found = True
    return total if found else None


def _is_sentence_transformers_library(info: HubModelInfo) -> bool:
    """Strict: Hub library_name must be sentence-transformers (loadable via ST)."""
    return (info.library_name or "").lower() == "sentence-transformers"


def _is_excluded_format(info: HubModelInfo) -> bool:
    mid = info.id.lower()
    tags = {t.lower() for t in info.tags}
    needles = ("gguf", "mlx", "onnx", "openvino", "tensorrt")
    if any(n in mid for n in needles):
        return True
    if tags & set(needles):
        return True
    return False


def _is_st_embedding(info: HubModelInfo) -> bool:
    if not _is_sentence_transformers_library(info) or _is_excluded_format(info):
        return False
    return info.pipeline_tag in {
        None,
        "feature-extraction",
        "sentence-similarity",
    }


def _is_st_rerank(info: HubModelInfo) -> bool:
    if not _is_sentence_transformers_library(info) or _is_excluded_format(info):
        return False
    return _looks_like_cross_encoder(info)


def _looks_like_cross_encoder(info: HubModelInfo) -> bool:
    mid = info.id.lower()
    tags = {t.lower() for t in info.tags}
    if "cross-encoder" in mid or mid.startswith("cross-encoder/"):
        return True
    if "cross-encoder" in tags or "text-ranking" in tags:
        return True
    if info.pipeline_tag in {"text-ranking", "sentence-similarity"}:
        return "cross" in mid or "rerank" in mid or "ms-marco" in mid
    return "rerank" in mid or "ms-marco" in mid

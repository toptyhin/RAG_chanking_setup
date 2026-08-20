"""Scan local Hugging Face / sentence-transformers cache dirs for repo ids."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class CachedHubModel:
    model_id: str
    size_bytes: int | None
    cache_roots: tuple[str, ...]


def _hub_dir_to_repo_id(dirname: str) -> str | None:
    """``models--org--name`` → ``org/name``."""
    if not dirname.startswith("models--"):
        return None
    rest = dirname.removeprefix("models--")
    if not rest or "--" not in rest:
        # Single-segment ids are unusual for Hub repos we care about.
        return rest.replace("--", "/") if rest else None
    return rest.replace("--", "/")


def _dir_size_bytes(path: Path) -> int | None:
    if not path.is_dir():
        return None
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += (Path(root) / name).stat().st_size
                except OSError:
                    continue
    except OSError:
        return None
    return total


def default_cache_roots() -> list[Path]:
    """Resolve HF / ST cache roots from env (Compose mounts these under /models)."""
    roots: list[Path] = []
    seen: set[Path] = set()

    def add(raw: str | None) -> None:
        if not raw:
            return
        path = Path(raw).expanduser()
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen:
            return
        seen.add(resolved)
        roots.append(path)

    add(os.environ.get("HUGGINGFACE_HUB_CACHE"))
    add(os.environ.get("SENTENCE_TRANSFORMERS_HOME"))
    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        add(str(Path(hf_home) / "hub"))
        add(str(Path(hf_home) / "sentence-transformers"))

    # Dev fallback only when Compose/env did not configure any cache root.
    if not roots:
        add(str(Path.home() / ".cache" / "huggingface" / "hub"))
        add(str(Path.home() / ".cache" / "torch" / "sentence_transformers"))
    return roots


def list_cached_hub_models(
    *,
    roots: list[Path] | None = None,
    query: str = "",
) -> list[CachedHubModel]:
    """Return Hub repo ids present as ``models--*`` directories under cache roots."""
    q = query.strip().lower()
    by_id: dict[str, CachedHubModel] = {}

    for root in roots if roots is not None else default_cache_roots():
        if not root.is_dir():
            continue
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir():
                continue
            model_id = _hub_dir_to_repo_id(entry.name)
            if not model_id or "/" not in model_id:
                continue
            if q and q not in model_id.lower():
                continue
            size = _dir_size_bytes(entry)
            existing = by_id.get(model_id)
            if existing is None:
                by_id[model_id] = CachedHubModel(
                    model_id=model_id,
                    size_bytes=size,
                    cache_roots=(str(root),),
                )
            else:
                merged_size = existing.size_bytes
                if size is not None:
                    merged_size = max(merged_size or 0, size)
                by_id[model_id] = CachedHubModel(
                    model_id=model_id,
                    size_bytes=merged_size,
                    cache_roots=tuple(
                        dict.fromkeys([*existing.cache_roots, str(root)])
                    ),
                )

    return sorted(by_id.values(), key=lambda m: m.model_id.lower())

"""In-process embedding/rerank model registry with load jobs and progress."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from rageval_cache_fs import FsEmbeddingCache
from rageval_embedding import (
    DEFAULT_MODEL,
    EmbeddingService,
    HashEmbeddingProvider,
    SentenceTransformerProvider,
)
from rageval_embedding_providers import (
    EmbeddingConfig,
    build_embedding_provider,
    is_remote_embedding_provider,
)
from rageval_hf_hub import HfHubCatalog, HubModelInfo
from rageval_hf_hub.local_cache import list_cached_hub_models
from rageval_llm_providers.config import LlmConfig
from rageval_llm_providers.rerank import (
    OllamaGenerativeRerankProvider,
    RerankConfig,
    RerankProviderKind,
    resolve_rerank_provider,
)
from rageval_rerank import (
    DEFAULT_CROSS_ENCODER,
    CrossEncoderRerankProvider,
    ReverseRerankProvider,
    RerankProvider,
)

logger = logging.getLogger(__name__)

Stage = Literal["queued", "downloading", "loading", "ready", "failed"]


class ModelKind(str, Enum):
    EMBEDDING = "embedding"
    RERANK = "rerank"


class MlNotAvailableError(RuntimeError):
    """Raised when sentence-transformers / torch are not installed."""


@dataclass
class LoadJob:
    job_id: str
    kind: ModelKind
    model_id: str
    stage: Stage = "queued"
    percent: float = 0.0
    message: str = ""
    error: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind.value,
            "model_id": self.model_id,
            "stage": self.stage,
            "percent": self.percent,
            "message": self.message,
            "error": self.error,
            "status": self.stage,
        }


@dataclass
class _EmbeddingEntry:
    model_id: str
    service: EmbeddingService


@dataclass
class _RerankEntry:
    model_id: str
    provider: RerankProvider


def ml_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


class ModelRegistry:
    """LRU cache of loaded models + async load jobs with progress."""

    def __init__(
        self,
        *,
        cache_dir: Path,
        catalog: HfHubCatalog,
        default_embedding: EmbeddingService,
        default_embedding_model: str,
        default_rerank_model: str = DEFAULT_CROSS_ENCODER,
        hf_token: str | None = None,
        max_embedding: int = 2,
        max_rerank: int = 2,
        validate_on_load: bool = True,
        embedding_config_loader: Callable[[], EmbeddingConfig] | None = None,
        rerank_config_loader: Callable[[], RerankConfig | None] | None = None,
        llm_config_loader: Callable[[], LlmConfig] | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.catalog = catalog
        self.hf_token = hf_token
        self.validate_on_load = validate_on_load
        self._embedding_config_loader = embedding_config_loader
        self._rerank_config_loader = rerank_config_loader
        self._llm_config_loader = llm_config_loader
        self._fs_cache = FsEmbeddingCache(self.cache_dir)
        self._default_embedding_model = default_embedding_model
        self._default_rerank_model = default_rerank_model
        self._current_embedding_model = default_embedding.provider.model_name
        self._current_rerank_model = default_rerank_model
        self._max_embedding = max_embedding
        self._max_rerank = max_rerank
        self._embeddings: OrderedDict[str, _EmbeddingEntry] = OrderedDict()
        self._reranks: OrderedDict[str, _RerankEntry] = OrderedDict()
        self._jobs: dict[str, LoadJob] = {}
        self._lock = threading.RLock()
        self._load_locks: dict[str, asyncio.Lock] = {}
        # Seed default (hash or ST already built at startup).
        self._embeddings[default_embedding.provider.model_name] = _EmbeddingEntry(
            model_id=default_embedding.provider.model_name,
            service=EmbeddingService(
                default_embedding.provider,
                cache=self._fs_cache,
                dimension=(
                    None
                    if default_embedding.dimension == default_embedding.provider.dimension
                    else default_embedding.dimension
                ),
            ),
        )
        # Test double always available without ML.
        self._reranks["reverse"] = _RerankEntry(
            model_id="reverse",
            provider=ReverseRerankProvider(),
        )

    @property
    def default_embedding_model(self) -> str:
        return self._default_embedding_model

    @property
    def default_rerank_model(self) -> str:
        return self._default_rerank_model

    @property
    def current_embedding_model(self) -> str:
        return self._current_embedding_model

    def set_current_embedding_model(self, model_id: str) -> None:
        with self._lock:
            if model_id not in self._embeddings:
                raise LookupError(f"embedding model not loaded: {model_id}")
            self._current_embedding_model = model_id

    @property
    def current_rerank_model(self) -> str:
        return self._current_rerank_model

    def set_current_rerank_model(self, model_id: str) -> None:
        mid = model_id.strip()
        if not mid:
            raise ValueError("model_id is required")
        with self._lock:
            self._current_rerank_model = mid

    def search(self, kind: ModelKind, *, query: str = "", limit: int = 20) -> list[HubModelInfo]:
        remote = self.catalog.search(kind.value, query=query, limit=limit)  # type: ignore[arg-type]
        cached = list_cached_hub_models(query=query)
        if not cached:
            return remote

        cached_ids = {c.model_id for c in cached}
        remote_ids = {m.id for m in remote}
        pipeline = (
            "feature-extraction" if kind is ModelKind.EMBEDDING else "text-ranking"
        )

        # Volume-only models (not in the Hub search page) first.
        pinned: list[HubModelInfo] = [
            HubModelInfo(
                id=row.model_id,
                downloads=0,
                likes=0,
                pipeline_tag=pipeline,
                tags=["local-cache"],
                library_name="sentence-transformers",
                size_bytes=row.size_bytes,
            )
            for row in cached
            if row.model_id not in remote_ids
        ]

        # Among Hub hits, surface ones already on disk first.
        on_disk = [m for m in remote if m.id in cached_ids]
        rest = [m for m in remote if m.id not in cached_ids]

        out: list[HubModelInfo] = []
        seen: set[str] = set()
        for m in [*pinned, *on_disk, *rest]:
            if m.id in seen:
                continue
            seen.add(m.id)
            out.append(m)
            # Keep every volume match, then fill with Hub results up to ``limit``.
            if len(out) >= len(pinned) + len(on_disk) and len(out) >= limit:
                break
        return out

    def storage_sizes(self, model_ids: list[str]) -> dict[str, int | None]:
        # Prefer local volume size when present; fall back to Hub usedStorage.
        local = {
            row.model_id: row.size_bytes
            for row in list_cached_hub_models()
            if row.model_id in model_ids
        }
        missing = [mid for mid in model_ids if local.get(mid) is None]
        remote = self.catalog.get_used_storage_many(missing) if missing else {}
        return {mid: local.get(mid, remote.get(mid)) for mid in model_ids}

    def list_loaded(self, kind: ModelKind) -> list[dict[str, Any]]:
        with self._lock:
            if kind is ModelKind.EMBEDDING:
                return [
                    {
                        "model_id": e.model_id,
                        "dimension": e.service.dimension,
                        "current": e.model_id == self._current_embedding_model,
                    }
                    for e in self._embeddings.values()
                ]
            return [
                {
                    "model_id": e.model_id,
                    "current": e.model_id == self._current_rerank_model,
                }
                for e in self._reranks.values()
            ]

    def list_cached(self, kind: ModelKind, *, query: str = "") -> list[dict[str, Any]]:
        """Models whose weights are already on the local HF/ST volume."""
        cached = list_cached_hub_models(query=query)
        with self._lock:
            if kind is ModelKind.EMBEDDING:
                in_memory = set(self._embeddings.keys())
            else:
                in_memory = set(self._reranks.keys())
        return [
            {
                "model_id": row.model_id,
                "size_bytes": row.size_bytes,
                "in_memory": row.model_id in in_memory,
            }
            for row in cached
        ]

    def get_job(self, job_id: str) -> LoadJob | None:
        return self._jobs.get(job_id)

    def get_embedding_service(self, model_id: str | None = None) -> EmbeddingService:
        mid = model_id or self._current_embedding_model
        with self._lock:
            entry = self._embeddings.get(mid)
            if entry is None:
                raise LookupError(f"embedding model not loaded: {mid}")
            self._embeddings.move_to_end(mid)
            return entry.service

    def get_rerank_provider(self, model_id: str | None = None) -> RerankProvider:
        mid = model_id or self._current_rerank_model or self._default_rerank_model
        if mid in {"reverse", "test"}:
            return ReverseRerankProvider()
        with self._lock:
            entry = self._reranks.get(mid)
            if entry is None:
                raise LookupError(f"rerank model not loaded: {mid}")
            self._reranks.move_to_end(mid)
            return entry.provider

    def start_load(self, kind: ModelKind, model_id: str) -> LoadJob:
        model_id = model_id.strip()
        if not model_id:
            raise ValueError("model_id is required")

        with self._lock:
            if kind is ModelKind.EMBEDDING and model_id in self._embeddings:
                job = LoadJob(
                    job_id=str(uuid.uuid4()),
                    kind=kind,
                    model_id=model_id,
                    stage="ready",
                    percent=100.0,
                    message="already loaded",
                )
                self._jobs[job.job_id] = job
                return job
            if kind is ModelKind.RERANK and model_id in self._reranks:
                job = LoadJob(
                    job_id=str(uuid.uuid4()),
                    kind=kind,
                    model_id=model_id,
                    stage="ready",
                    percent=100.0,
                    message="already loaded",
                )
                self._jobs[job.job_id] = job
                return job

        if kind is ModelKind.EMBEDDING and _is_hash_model(model_id):
            return _load_hash_embedding(self, model_id)
        if kind is ModelKind.EMBEDDING and _remote_embedding_config(self) is not None:
            return _load_remote_embedding(self, model_id)
        if kind is ModelKind.RERANK and model_id in {"reverse", "test"}:
            job = LoadJob(
                job_id=str(uuid.uuid4()),
                kind=kind,
                model_id="reverse",
                stage="ready",
                percent=100.0,
                message="test reverse reranker",
            )
            self._jobs[job.job_id] = job
            return job
        if kind is ModelKind.RERANK:
            rerank_kind = _rerank_provider_kind(self, model_id)
            if rerank_kind is RerankProviderKind.ollama:
                return _load_remote_rerank(self, model_id)
            if rerank_kind in {RerankProviderKind.openrouter, RerankProviderKind.gigachat}:
                raise ValueError(
                    f"rerank runtime for provider {rerank_kind.value!r} is not "
                    "implemented; choose Ollama or Hugging Face"
                )

        if not ml_available():
            raise MlNotAvailableError(
                'ML extras required: pip install -e ".[ml]" '
                "(sentence-transformers + torch)"
            )

        if self.validate_on_load and not _is_hash_model(model_id):
            self.catalog.validate_for_kind(kind.value, model_id)  # type: ignore[arg-type]

        job = LoadJob(
            job_id=str(uuid.uuid4()),
            kind=kind,
            model_id=model_id,
            stage="queued",
            percent=0.0,
            message="queued",
        )
        self._jobs[job.job_id] = job
        return job

    async def run_load_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        if job.stage == "ready":
            return
        key = f"{job.kind.value}:{job.model_id}"
        lock = self._load_locks.setdefault(key, asyncio.Lock())
        async with lock:
            job = self._jobs.get(job_id)
            if job is None or job.stage == "ready":
                return
            try:
                await asyncio.to_thread(_load_sync, self, job)
            except Exception as exc:  # noqa: BLE001
                job.stage = "failed"
                job.error = str(exc)
                job.message = str(exc)
                job.percent = 0.0
                logger.exception("model load failed: %s %s", job.kind, job.model_id)

    async def ensure_embedding(self, model_id: str | None = None) -> EmbeddingService:
        mid = (model_id or self._current_embedding_model).strip()
        try:
            return self.get_embedding_service(mid)
        except LookupError:
            pass
        job = self.start_load(ModelKind.EMBEDDING, mid)
        if job.stage != "ready":
            await self.run_load_job(job.job_id)
        if job.stage == "failed":
            raise RuntimeError(job.error or "embedding load failed")
        return self.get_embedding_service(mid)

    async def ensure_rerank(self, model_id: str | None = None) -> RerankProvider:
        mid = (model_id or self._default_rerank_model).strip()
        if mid in {"reverse", "test"}:
            return ReverseRerankProvider()
        try:
            return self.get_rerank_provider(mid)
        except LookupError:
            pass
        job = self.start_load(ModelKind.RERANK, mid)
        if job.stage != "ready":
            await self.run_load_job(job.job_id)
        if job.stage == "failed":
            raise RuntimeError(job.error or "rerank load failed")
        return self.get_rerank_provider(mid)

    def resolve_embedding_sync(self, model_id: str) -> EmbeddingService:
        """Sync resolve for orchestrator grid points (model must be loaded or hash)."""
        mid = model_id.strip()
        try:
            return self.get_embedding_service(mid)
        except LookupError:
            if _is_hash_model(mid):
                _load_hash_embedding(self, mid)
                return self.get_embedding_service(mid)
            if _remote_embedding_config(self) is not None:
                _load_remote_embedding(self, mid)
                return self.get_embedding_service(mid)
            raise

    def resolve_rerank_sync(self, model_id: str) -> RerankProvider:
        mid = model_id.strip()
        if mid in {"reverse", "test"}:
            return ReverseRerankProvider()
        try:
            return self.get_rerank_provider(mid)
        except LookupError:
            if _rerank_provider_kind(self, mid) is RerankProviderKind.ollama:
                _load_remote_rerank(self, mid)
                return self.get_rerank_provider(mid)
            raise


def _rerank_provider_kind(
    registry: ModelRegistry,
    model_id: str,
) -> RerankProviderKind:
    config: RerankConfig | None = None
    if registry._rerank_config_loader is not None:
        config = registry._rerank_config_loader()
    return resolve_rerank_provider(config, model_id)


def _load_remote_rerank(registry: ModelRegistry, model_id: str) -> LoadJob:
    llm = (
        registry._llm_config_loader()
        if registry._llm_config_loader is not None
        else LlmConfig()
    )
    provider = OllamaGenerativeRerankProvider(
        base_url=llm.ollama.base_url,
        model=model_id,
    )
    with registry._lock:
        registry._reranks[model_id] = _RerankEntry(
            model_id=model_id, provider=provider
        )
        registry._reranks.move_to_end(model_id)
        registry._current_rerank_model = model_id
        while len(registry._reranks) > registry._max_rerank:
            oldest_key, _ = next(iter(registry._reranks.items()))
            if oldest_key == "reverse" and len(registry._reranks) > 1:
                keys = list(registry._reranks.keys())
                victim = next(key for key in keys if key != "reverse")
                registry._reranks.pop(victim)
            else:
                if oldest_key == "reverse":
                    break
                registry._reranks.popitem(last=False)
    job = LoadJob(
        job_id=str(uuid.uuid4()),
        kind=ModelKind.RERANK,
        model_id=model_id,
        stage="ready",
        percent=100.0,
        message="remote rerank ready (ollama)",
    )
    registry._jobs[job.job_id] = job
    return job


def _remote_embedding_config(registry: ModelRegistry) -> EmbeddingConfig | None:
    if registry._embedding_config_loader is None:
        return None
    config = registry._embedding_config_loader()
    if not is_remote_embedding_provider(config.provider):
        return None
    return config


def _load_hash_embedding(registry: ModelRegistry, model_id: str) -> LoadJob:
    dim = 32
    if model_id.startswith("hash-emb-d"):
        try:
            dim = int(model_id.removeprefix("hash-emb-d"))
        except ValueError:
            dim = 32
    provider = HashEmbeddingProvider(model_name=model_id, dimension=dim)
    service = EmbeddingService(provider, cache=registry._fs_cache)
    with registry._lock:
        registry._embeddings[model_id] = _EmbeddingEntry(model_id=model_id, service=service)
        registry._embeddings.move_to_end(model_id)
        while len(registry._embeddings) > registry._max_embedding:
            registry._embeddings.popitem(last=False)
    job = LoadJob(
        job_id=str(uuid.uuid4()),
        kind=ModelKind.EMBEDDING,
        model_id=model_id,
        stage="ready",
        percent=100.0,
        message="hash embedding ready",
    )
    registry._jobs[job.job_id] = job
    return job


def _load_remote_embedding(registry: ModelRegistry, model_id: str) -> LoadJob:
    config = _remote_embedding_config(registry)
    if config is None:
        raise LookupError(f"remote embedding config unavailable for: {model_id}")
    provider = build_embedding_provider(config, model_id=model_id)
    if provider is None:
        raise LookupError(f"cannot build remote embedding provider for: {model_id}")
    service = EmbeddingService(provider, cache=registry._fs_cache)
    with registry._lock:
        registry._embeddings[model_id] = _EmbeddingEntry(model_id=model_id, service=service)
        registry._embeddings.move_to_end(model_id)
        while len(registry._embeddings) > registry._max_embedding:
            registry._embeddings.popitem(last=False)
    job = LoadJob(
        job_id=str(uuid.uuid4()),
        kind=ModelKind.EMBEDDING,
        model_id=model_id,
        stage="ready",
        percent=100.0,
        message=f"remote embedding ready ({config.provider.value})",
    )
    registry._jobs[job.job_id] = job
    return job


def _load_sync(registry: ModelRegistry, job: LoadJob) -> None:
    job.stage = "downloading"
    job.percent = 5.0
    job.message = "downloading weights"

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise MlNotAvailableError(
            'ML extras required: pip install -e ".[ml]"'
        ) from exc

    revision = _hub_revision_for(job.model_id, token=registry.hf_token)
    snapshot_download(
        repo_id=job.model_id,
        revision=revision,
        token=registry.hf_token,
        tqdm_class=_job_tqdm_class(job),
    )

    job.stage = "loading"
    job.percent = 85.0
    job.message = "loading model into memory"

    if job.kind is ModelKind.EMBEDDING:
        provider = SentenceTransformerProvider(model_name=job.model_id)
        service = EmbeddingService(provider, cache=registry._fs_cache)
        with registry._lock:
            registry._embeddings[job.model_id] = _EmbeddingEntry(
                model_id=job.model_id, service=service
            )
            registry._embeddings.move_to_end(job.model_id)
            while len(registry._embeddings) > registry._max_embedding:
                registry._embeddings.popitem(last=False)
    else:
        provider = CrossEncoderRerankProvider(model_name=job.model_id)
        with registry._lock:
            registry._reranks[job.model_id] = _RerankEntry(
                model_id=job.model_id, provider=provider
            )
            registry._reranks.move_to_end(job.model_id)
            registry._current_rerank_model = job.model_id
            while len(registry._reranks) > registry._max_rerank:
                oldest_key, _ = next(iter(registry._reranks.items()))
                if oldest_key == "reverse" and len(registry._reranks) > 1:
                    keys = list(registry._reranks.keys())
                    victim = next(k for k in keys if k != "reverse")
                    registry._reranks.pop(victim)
                else:
                    if oldest_key == "reverse":
                        break
                    registry._reranks.popitem(last=False)

    job.stage = "ready"
    job.percent = 100.0
    job.message = "ready"


def _is_hash_model(model_id: str) -> bool:
    return model_id.startswith("hash-emb") or model_id in {"hash", "hash-emb-v1", "test"}


def _hub_revision_for(model_id: str, *, token: str | None = None) -> str:
    """Resolve an immutable commit SHA for Hub downloads (bandit B615)."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return "main"
    try:
        info = HfApi(token=token).model_info(model_id)
        sha = getattr(info, "sha", None)
        if isinstance(sha, str) and len(sha) >= 7:
            return sha
    except Exception:  # noqa: BLE001
        logger.warning("could not resolve Hub revision for %s; falling back to main", model_id)
    return "main"


def _job_tqdm_class(job: LoadJob) -> type:
    """tqdm subclass compatible with huggingface_hub.snapshot_download."""
    from tqdm.auto import tqdm as std_tqdm

    class _JobTqdm(std_tqdm):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs.setdefault("disable", False)
            super().__init__(*args, **kwargs)
            self._sync_job()

        def update(self, n: float | int = 1) -> bool | None:
            result = super().update(n)
            self._sync_job()
            return result

        def close(self) -> None:
            self._sync_job()
            super().close()

        def _sync_job(self) -> None:
            total = float(self.total or 0)
            if total > 0:
                frac = min(1.0, float(self.n) / total)
                job.percent = 5.0 + frac * 75.0
                job.message = f"downloading {int(frac * 100)}%"
            else:
                job.message = "downloading…"

    return _JobTqdm


def build_registry(
    *,
    cache_dir: Path,
    default_embedding: EmbeddingService,
    embedding_model: str,
    rerank_model: str = DEFAULT_CROSS_ENCODER,
    hf_token: str | None = None,
    validate_on_load: bool = True,
    embedding_config_loader: Callable[[], EmbeddingConfig] | None = None,
    rerank_config_loader: Callable[[], RerankConfig | None] | None = None,
    llm_config_loader: Callable[[], LlmConfig] | None = None,
) -> ModelRegistry:
    catalog = HfHubCatalog(token=hf_token)
    return ModelRegistry(
        cache_dir=cache_dir,
        catalog=catalog,
        default_embedding=default_embedding,
        default_embedding_model=embedding_model or DEFAULT_MODEL,
        default_rerank_model=rerank_model or DEFAULT_CROSS_ENCODER,
        hf_token=hf_token,
        validate_on_load=validate_on_load,
        embedding_config_loader=embedding_config_loader,
        rerank_config_loader=rerank_config_loader,
        llm_config_loader=llm_config_loader,
    )

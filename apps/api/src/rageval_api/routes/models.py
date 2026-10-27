"""Embedding / rerank model catalog, load jobs, and progress SSE."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from rageval_api.model_registry import MlNotAvailableError, ModelKind, ModelRegistry
from rageval_llm_providers.rerank import (
    RerankConfigStore,
    RerankProviderKind,
    resolve_rerank_provider,
)

logger = logging.getLogger("rageval.models.storage")

router = APIRouter(prefix="/models", tags=["models"])


class LoadRequest(BaseModel):
    model_id: str = Field(min_length=1)


class LoadResponse(BaseModel):
    job_id: str
    model_id: str
    status: str
    stage: str
    percent: float
    message: str


class HubModelOut(BaseModel):
    id: str
    downloads: int
    likes: int
    pipeline_tag: str | None = None
    tags: list[str] = Field(default_factory=list)
    library_name: str | None = None


class SearchResponse(BaseModel):
    items: list[HubModelOut]


class StorageRequest(BaseModel):
    model_ids: list[str] = Field(default_factory=list, max_length=50)


class StorageItemOut(BaseModel):
    model_id: str
    size_bytes: int | None = None


class StorageResponse(BaseModel):
    items: list[StorageItemOut]


class LoadedEmbeddingOut(BaseModel):
    model_id: str
    dimension: int
    current: bool = False


class LoadedRerankOut(BaseModel):
    model_id: str
    current: bool = False


class CachedModelOut(BaseModel):
    model_id: str
    size_bytes: int | None = None
    in_memory: bool = False


class CurrentEmbeddingOut(BaseModel):
    model_id: str
    dimension: int
    default_model: str


class CurrentRerankOut(BaseModel):
    model_id: str
    default_model: str
    provider: str | None = None


class SetCurrentRequest(BaseModel):
    model_id: str = Field(min_length=1)
    provider: str | None = None


def _registry(request: Request) -> ModelRegistry:
    reg = getattr(request.app.state, "model_registry", None)
    if reg is None:
        raise HTTPException(status_code=503, detail="model registry not initialized")
    return reg


def _rerank_store(request: Request) -> RerankConfigStore:
    store = getattr(request.app.state, "rerank_config_store", None)
    if store is None:
        store = RerankConfigStore(
            Path(request.app.state.settings.data_dir) / "rerank_config.json"
        )
        request.app.state.rerank_config_store = store
    return store


@router.post("/storage", response_model=StorageResponse)
async def fetch_model_storage(body: StorageRequest, request: Request) -> StorageResponse:
    """Lazy-load approximate download size (HF usedStorage) for listed model ids."""
    reg = _registry(request)
    ids = [m.strip() for m in body.model_ids if m and m.strip()][:50]
    if not ids:
        return StorageResponse(items=[])
    logger.info("storage size lookup for %d model(s)", len(ids))
    try:
        sizes = await asyncio.to_thread(reg.storage_sizes, ids)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Hugging Face storage lookup failed: {exc}"
        ) from exc
    found = sum(1 for mid in ids if sizes.get(mid) is not None)
    logger.info("storage size lookup done: %d/%d have size", found, len(ids))
    return StorageResponse(
        items=[
            StorageItemOut(model_id=mid, size_bytes=sizes.get(mid))
            for mid in ids
        ]
    )


@router.get("/embedding/search", response_model=SearchResponse)
async def search_embedding_models(
    request: Request,
    q: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    reg = _registry(request)
    try:
        items = await asyncio.to_thread(reg.search, ModelKind.EMBEDDING, query=q, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Hugging Face search failed: {exc}") from exc
    return SearchResponse(
        items=[
            HubModelOut(
                id=m.id,
                downloads=m.downloads,
                likes=m.likes,
                pipeline_tag=m.pipeline_tag,
                tags=m.tags,
                library_name=m.library_name,
            )
            for m in items
        ]
    )


@router.get("/rerank/search", response_model=SearchResponse)
async def search_rerank_models(
    request: Request,
    q: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    reg = _registry(request)
    try:
        items = await asyncio.to_thread(reg.search, ModelKind.RERANK, query=q, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Hugging Face search failed: {exc}") from exc
    return SearchResponse(
        items=[
            HubModelOut(
                id=m.id,
                downloads=m.downloads,
                likes=m.likes,
                pipeline_tag=m.pipeline_tag,
                tags=m.tags,
                library_name=m.library_name,
            )
            for m in items
        ]
    )


@router.get("/embedding/loaded", response_model=list[LoadedEmbeddingOut])
async def list_loaded_embeddings(request: Request) -> list[LoadedEmbeddingOut]:
    reg = _registry(request)
    return [LoadedEmbeddingOut(**row) for row in reg.list_loaded(ModelKind.EMBEDDING)]


@router.get("/rerank/loaded", response_model=list[LoadedRerankOut])
async def list_loaded_reranks(request: Request) -> list[LoadedRerankOut]:
    reg = _registry(request)
    return [LoadedRerankOut(**row) for row in reg.list_loaded(ModelKind.RERANK)]


@router.get("/embedding/cached", response_model=list[CachedModelOut])
async def list_cached_embeddings(
    request: Request,
    q: str = Query(default=""),
) -> list[CachedModelOut]:
    """Models whose weights are already on the HF/ST volume."""
    reg = _registry(request)
    return [CachedModelOut(**row) for row in reg.list_cached(ModelKind.EMBEDDING, query=q)]


@router.get("/rerank/cached", response_model=list[CachedModelOut])
async def list_cached_reranks(
    request: Request,
    q: str = Query(default=""),
) -> list[CachedModelOut]:
    reg = _registry(request)
    return [CachedModelOut(**row) for row in reg.list_cached(ModelKind.RERANK, query=q)]


@router.get("/embedding/current", response_model=CurrentEmbeddingOut)
async def get_current_embedding(request: Request) -> CurrentEmbeddingOut:
    reg = _registry(request)
    service = reg.get_embedding_service()
    return CurrentEmbeddingOut(
        model_id=reg.current_embedding_model,
        dimension=service.dimension,
        default_model=reg.default_embedding_model,
    )


@router.put("/embedding/current", response_model=CurrentEmbeddingOut)
async def set_current_embedding(body: SetCurrentRequest, request: Request) -> CurrentEmbeddingOut:
    reg = _registry(request)
    try:
        reg.set_current_embedding_model(body.model_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    service = reg.get_embedding_service()
    return CurrentEmbeddingOut(
        model_id=reg.current_embedding_model,
        dimension=service.dimension,
        default_model=reg.default_embedding_model,
    )


@router.get("/rerank/current", response_model=CurrentRerankOut)
async def get_current_rerank(request: Request) -> CurrentRerankOut:
    reg = _registry(request)
    model_id = reg.current_rerank_model
    provider = resolve_rerank_provider(_rerank_store(request).load_or_none(), model_id)
    return CurrentRerankOut(
        model_id=model_id,
        default_model=reg.default_rerank_model,
        provider=provider.value,
    )


@router.put("/rerank/current", response_model=CurrentRerankOut)
async def set_current_rerank(body: SetCurrentRequest, request: Request) -> CurrentRerankOut:
    reg = _registry(request)
    store = _rerank_store(request)
    provider = body.provider.strip() if body.provider else None
    if provider:
        try:
            RerankProviderKind(provider)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"unsupported rerank provider: {provider!r}",
            ) from exc
    else:
        provider = resolve_rerank_provider(store.load_or_none(), body.model_id).value

    try:
        reg.set_current_rerank_model(body.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.merge_update({"model": body.model_id, "provider": provider})
    return CurrentRerankOut(
        model_id=reg.current_rerank_model,
        default_model=reg.default_rerank_model,
        provider=provider,
    )


async def _start_load(request: Request, kind: ModelKind, model_id: str) -> LoadResponse:
    reg = _registry(request)
    try:
        job = reg.start_load(kind, model_id)
    except MlNotAvailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if job.stage != "ready":
        runner = request.app.state.task_runner
        job_id = job.job_id

        async def _job() -> None:
            await reg.run_load_job(job_id)

        try:
            runner.submit(f"model-load-{job_id}", _job)
        except RuntimeError:
            # Already running — ignore.
            pass

    return LoadResponse(
        job_id=job.job_id,
        model_id=job.model_id,
        status=job.stage,
        stage=job.stage,
        percent=job.percent,
        message=job.message,
    )


@router.post("/embedding/load", response_model=LoadResponse)
async def load_embedding(body: LoadRequest, request: Request) -> LoadResponse:
    return await _start_load(request, ModelKind.EMBEDDING, body.model_id)


@router.post("/rerank/load", response_model=LoadResponse)
async def load_rerank(body: LoadRequest, request: Request) -> LoadResponse:
    return await _start_load(request, ModelKind.RERANK, body.model_id)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict:
    reg = _registry(request)
    job = reg.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.snapshot()


@router.get("/jobs/{job_id}/progress")
async def job_progress_sse(job_id: str, request: Request) -> StreamingResponse:
    reg = _registry(request)

    async def event_gen():
        terminal = {"ready", "failed"}
        while True:
            if await request.is_disconnected():
                break
            job = reg.get_job(job_id)
            if job is None:
                payload = {"error": "not found"}
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                break
            payload = job.snapshot()
            yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
            if job.stage in terminal:
                event = "done" if job.stage == "ready" else "error"
                yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
                break
            await asyncio.sleep(2.0)

    return StreamingResponse(event_gen(), media_type="text/event-stream")

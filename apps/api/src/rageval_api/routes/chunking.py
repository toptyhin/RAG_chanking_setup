from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from rageval_api.deps import ArtifactRepoDep, ObjectStoreDep, ProjectRepoDep
from rageval_api.routes.artifacts import _to_out
from rageval_api.schemas import ArtifactOut
from rageval_api.services.artifact_io import load_artifact_model, persist_artifact_model
from rageval_api.services.artifact_meta import diagnose_empty_corpus
from rageval_api.services.artifact_naming import naming_meta, source_name_from_record
from rageval_api.services.chunk_length_stats import length_chars_from_chunks
from rageval_chunking import (
    REFERENCE_PIPELINE_ID,
    chunk_corpus,
    chunk_fixed_size,
    list_providers,
    parse_chunker_options,
)
from rageval_domain import ArtifactType, Chunk, ChunkSet, CleanCorpus
from rageval_llm_providers.limits import estimate_tokens

router = APIRouter(tags=["chunking"])


class ReferenceChunkRequest(BaseModel):
    clean_corpus_id: str
    size: int = Field(default=512, gt=0)
    overlap: int = Field(default=64, ge=0)


class ByoChunkItem(BaseModel):
    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    start_char: int | None = None
    end_char: int | None = None
    meta: dict = Field(default_factory=dict)


class ByoChunkImportRequest(BaseModel):
    chunks: list[ByoChunkItem] = Field(min_length=1)
    chunk_pipeline_id: str = "byo"
    parent_ids: list[str] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


class ChunkSetResponse(BaseModel):
    artifact: ArtifactOut
    chunk_count: int


class ChunkerProviderOut(BaseModel):
    id: str
    label: str
    modes: list[str]
    available: bool
    options_schema: dict[str, Any]
    unavailable_reason: str | None = None


class UnifiedChunkRequest(BaseModel):
    clean_corpus_id: str
    provider: str
    # Remaining knobs are provider-specific; validated via parse_chunker_options.
    model_config = {"extra": "allow"}


class ChunkPreviewRequest(UnifiedChunkRequest):
    preview_count: int = Field(default=5, ge=3, le=20)


class ChunkPreviewItem(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    size_chars: int
    size_tokens: int
    start_char: int | None = None
    end_char: int | None = None


class ChunkSizeStats(BaseModel):
    min_chars: int
    p50_chars: int
    p95_chars: int
    max_chars: int
    average_chars: float
    min_tokens: int
    p50_tokens: int
    p95_tokens: int
    max_tokens: int
    average_tokens: float
    tokens_note: str | None = None


class ChunkPreviewResponse(BaseModel):
    chunk_count: int
    document_count: int
    total_chars: int
    size: ChunkSizeStats
    samples: list[ChunkPreviewItem]
    persisted: bool = False


@router.get("/chunkers", response_model=list[ChunkerProviderOut])
async def get_chunkers() -> list[ChunkerProviderOut]:
    return [
        ChunkerProviderOut(
            id=p.id,
            label=p.label,
            modes=p.modes,
            available=p.available,
            options_schema=p.options_schema,
            unavailable_reason=p.unavailable_reason,
        )
        for p in list_providers()
    ]


async def _load_project_corpus(
    project_id: str,
    clean_corpus_id: str,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[Any, CleanCorpus]:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        clean_record, corpus = await load_artifact_model(
            artifacts,
            store,
            clean_corpus_id,
            CleanCorpus,
            expected_type=ArtifactType.CLEAN_CORPUS.value,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="clean_corpus not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if clean_record.project_id != project_id:
        raise HTTPException(status_code=400, detail="clean_corpus belongs to another project")
    return clean_record, corpus


def _parse_options(raw: dict[str, Any]):
    try:
        return parse_chunker_options(raw)
    except ValidationError as exc:
        messages = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", ()))
            msg = err.get("msg", "validation error")
            messages.append(f"{loc}: {msg}" if loc else msg)
        raise HTTPException(
            status_code=400,
            detail="; ".join(messages) or "invalid chunker options",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _run_chunker(corpus: CleanCorpus, options: Any) -> ChunkSet:
    try:
        return chunk_corpus(corpus, options)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _sample_chunks(chunks: list[Chunk], count: int) -> list[Chunk]:
    if len(chunks) <= count:
        return chunks
    indexes = {
        round(index * (len(chunks) - 1) / (count - 1))
        for index in range(count)
    }
    return [chunks[index] for index in sorted(indexes)]


@router.post(
    "/projects/{project_id}/chunk-sets/preview",
    response_model=ChunkPreviewResponse,
)
async def preview_chunk_set(
    project_id: str,
    body: ChunkPreviewRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> ChunkPreviewResponse:
    """Run a chunker without writing an artifact or object-store blob."""
    _, corpus = await _load_project_corpus(
        project_id, body.clean_corpus_id, projects, artifacts, store
    )
    raw = body.model_dump(exclude={"clean_corpus_id", "preview_count"})
    chunk_set = _run_chunker(corpus, _parse_options(raw))
    if not chunk_set.chunks:
        raise HTTPException(
            status_code=400,
            detail=diagnose_empty_corpus(corpus.documents),
        )

    stats = length_chars_from_chunks(chunk_set.chunks)
    assert stats is not None  # empty sets rejected above
    samples = _sample_chunks(chunk_set.chunks, body.preview_count)
    return ChunkPreviewResponse(
        chunk_count=len(chunk_set.chunks),
        document_count=len(corpus.documents),
        total_chars=sum(len(chunk.text) for chunk in chunk_set.chunks),
        size=ChunkSizeStats(**stats),
        samples=[
            ChunkPreviewItem(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                text=chunk.text,
                size_chars=len(chunk.text),
                size_tokens=estimate_tokens(chunk.text),
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )
            for chunk in samples
        ],
    )


async def _persist_chunk_set(
    *,
    project_id: str,
    corpus: CleanCorpus,
    clean_record: Any,
    chunk_set: ChunkSet,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
    extra_meta: dict[str, Any],
) -> ChunkSetResponse:
    if not chunk_set.chunks:
        raise HTTPException(
            status_code=400,
            detail=diagnose_empty_corpus(corpus.documents),
        )

    source = source_name_from_record(clean_record)
    pipeline_id = chunk_set.chunk_pipeline_id or "unknown"
    length_chars = length_chars_from_chunks(chunk_set.chunks)
    record = await persist_artifact_model(
        artifacts,
        store,
        model=chunk_set,
        artifact_id=chunk_set.id,
        project_id=project_id,
        artifact_type=ArtifactType.CHUNK_SET.value,
        parent_ids=[corpus.id],
        meta={
            "chunk_pipeline_id": pipeline_id,
            "chunk_count": len(chunk_set.chunks),
            **({"length_chars": length_chars} if length_chars else {}),
            **extra_meta,
            **naming_meta(ArtifactType.CHUNK_SET.value, source),
        },
    )
    return ChunkSetResponse(
        artifact=await _to_out(record, store, artifacts),
        chunk_count=len(chunk_set.chunks),
    )


@router.post(
    "/projects/{project_id}/chunk-sets",
    response_model=ChunkSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chunk_set(
    project_id: str,
    body: UnifiedChunkRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> ChunkSetResponse:
    clean_record, corpus = await _load_project_corpus(
        project_id, body.clean_corpus_id, projects, artifacts, store
    )

    raw = body.model_dump(exclude={"clean_corpus_id"})
    options = _parse_options(raw)
    chunk_set = _run_chunker(corpus, options)

    return await _persist_chunk_set(
        project_id=project_id,
        corpus=corpus,
        clean_record=clean_record,
        chunk_set=chunk_set,
        artifacts=artifacts,
        store=store,
        extra_meta={"options": options.model_dump()},
    )


@router.post(
    "/projects/{project_id}/chunk-sets/reference",
    response_model=ChunkSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reference_chunk_set(
    project_id: str,
    body: ReferenceChunkRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> ChunkSetResponse:
    clean_record, corpus = await _load_project_corpus(
        project_id, body.clean_corpus_id, projects, artifacts, store
    )

    try:
        chunk_set = chunk_fixed_size(corpus, size=body.size, overlap=body.overlap)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _persist_chunk_set(
        project_id=project_id,
        corpus=corpus,
        clean_record=clean_record,
        chunk_set=chunk_set,
        artifacts=artifacts,
        store=store,
        extra_meta={
            "chunk_pipeline_id": REFERENCE_PIPELINE_ID,
            "size": body.size,
            "overlap": body.overlap,
        },
    )


@router.post(
    "/projects/{project_id}/chunk-sets/import",
    response_model=ChunkSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_byo_chunk_set(
    project_id: str,
    body: ByoChunkImportRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> ChunkSetResponse:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")

    seen: set[str] = set()
    chunks: list[Chunk] = []
    for item in body.chunks:
        if item.chunk_id in seen:
            raise HTTPException(
                status_code=400, detail=f"duplicate chunk_id: {item.chunk_id}"
            )
        seen.add(item.chunk_id)
        chunks.append(
            Chunk(
                chunk_id=item.chunk_id,
                doc_id=item.doc_id,
                text=item.text,
                start_char=item.start_char,
                end_char=item.end_char,
                meta=item.meta,
            )
        )

    parent_source: str | None = None
    for parent_id in body.parent_ids:
        parent = await artifacts.get(parent_id)
        parent_source = source_name_from_record(parent)
        if parent_source:
            break
    byo_source = body.meta.get("source_name") if isinstance(body.meta.get("source_name"), str) else None
    source = byo_source or parent_source or "byo"

    chunk_set = ChunkSet(
        project_id=project_id,
        parent_ids=body.parent_ids,
        chunk_pipeline_id=body.chunk_pipeline_id,
        chunks=chunks,
        meta={"source": "byo", **body.meta},
    )
    length_chars = length_chars_from_chunks(chunks)
    record = await persist_artifact_model(
        artifacts,
        store,
        model=chunk_set,
        artifact_id=chunk_set.id,
        project_id=project_id,
        artifact_type=ArtifactType.CHUNK_SET.value,
        parent_ids=body.parent_ids,
        meta={
            "chunk_pipeline_id": body.chunk_pipeline_id,
            "chunk_count": len(chunks),
            **({"length_chars": length_chars} if length_chars else {}),
            "source": "byo",
            **naming_meta(ArtifactType.CHUNK_SET.value, source),
        },
    )
    return ChunkSetResponse(
        artifact=await _to_out(record, store, artifacts),
        chunk_count=len(chunks),
    )

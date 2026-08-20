from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from rageval_api.deps import ArtifactRepoDep, ObjectStoreDep, ProjectRepoDep
from rageval_api.routes.artifacts import _to_out
from rageval_api.schemas import ArtifactOut
from rageval_api.services.artifact_io import load_artifact_model, persist_artifact_model
from rageval_api.services.artifact_naming import naming_meta, source_name_from_record
from rageval_domain import ArtifactType, ChunkSet
from rageval_index import build_index
from rageval_vectordb_qdrant import QdrantVectorStore

router = APIRouter(tags=["index"])


class IndexRequest(BaseModel):
    chunk_set_id: str
    collection_name: str | None = None
    embedding_model: str | None = None


class IndexResponse(BaseModel):
    artifact: ArtifactOut
    collection_name: str
    build_time_sec: float
    vector_count: int
    cache_hit: bool


@router.post(
    "/projects/{project_id}/indexes",
    response_model=IndexResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_index(
    project_id: str,
    body: IndexRequest,
    request: Request,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> IndexResponse:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        chunk_record, chunk_set = await load_artifact_model(
            artifacts,
            store,
            body.chunk_set_id,
            ChunkSet,
            expected_type=ArtifactType.CHUNK_SET.value,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="chunk_set not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if chunk_record.project_id != project_id:
        raise HTTPException(status_code=400, detail="chunk_set belongs to another project")
    if not chunk_set.chunks:
        raise HTTPException(
            status_code=400,
            detail=f"chunk_set {body.chunk_set_id} has 0 chunks — cannot build index",
        )

    registry = request.app.state.model_registry
    try:
        embedding = await registry.ensure_embedding(body.embedding_model)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    qdrant: QdrantVectorStore = request.app.state.qdrant
    result = build_index(
        chunk_set,
        embedding=embedding,
        store=qdrant,
        collection_name=body.collection_name,
    )
    record = await persist_artifact_model(
        artifacts,
        store,
        model=result.index_run,
        artifact_id=result.index_run.id,
        project_id=project_id,
        artifact_type=ArtifactType.INDEX_RUN.value,
        parent_ids=[chunk_set.id],
        meta={
            "collection_name": result.collection_name,
            "vector_count": result.vector_count,
            "build_time_sec": result.build_time_sec,
            "cache_hit": result.cache_hit,
            "embedding_model": result.index_run.embedding_model,
            "dimension": result.index_run.dimension,
            **naming_meta(
                ArtifactType.INDEX_RUN.value,
                source_name_from_record(chunk_record),
            ),
        },
    )
    return IndexResponse(
        artifact=await _to_out(record, store, artifacts),
        collection_name=result.collection_name,
        build_time_sec=result.build_time_sec,
        vector_count=result.vector_count,
        cache_hit=result.cache_hit,
    )

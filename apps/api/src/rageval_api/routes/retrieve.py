from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rageval_api.deps import ArtifactRepoDep, ObjectStoreDep, ProjectRepoDep
from rageval_api.services.artifact_io import load_artifact_model
from rageval_domain import ArtifactType, IndexRun, TestSet
from rageval_eval import score_retrieval
from rageval_retrieval import dense_retrieve
from rageval_vectordb_qdrant import QdrantVectorStore

router = APIRouter(tags=["retrieval"])


class RetrieveRequest(BaseModel):
    index_run_id: str
    test_set_id: str
    top_k: int = Field(default=10, gt=0, le=100)


class QueryHitOut(BaseModel):
    query_id: str
    ranked_chunk_ids: list[str]
    scores: list[float]
    latency_ms: float


class RetrieveResponse(BaseModel):
    results: list[QueryHitOut]
    latency: dict
    metrics: dict


@router.post("/projects/{project_id}/retrieve", response_model=RetrieveResponse)
async def retrieve_dense(
    project_id: str,
    body: RetrieveRequest,
    request: Request,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> RetrieveResponse:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        index_record, index_run = await load_artifact_model(
            artifacts,
            store,
            body.index_run_id,
            IndexRun,
            expected_type=ArtifactType.INDEX_RUN.value,
        )
        test_record, test_set = await load_artifact_model(
            artifacts,
            store,
            body.test_set_id,
            TestSet,
            expected_type=ArtifactType.TEST_SET.value,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if index_record.project_id != project_id or test_record.project_id != project_id:
        raise HTTPException(status_code=400, detail="artifact belongs to another project")

    registry = request.app.state.model_registry
    try:
        embedding = await registry.ensure_embedding(index_run.embedding_model)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail=(
                f"cannot load embedding model {index_run.embedding_model!r} "
                f"for this index: {exc}"
            ),
        ) from exc
    qdrant: QdrantVectorStore = request.app.state.qdrant
    retrieval = dense_retrieve(
        test_set,
        collection_name=index_run.collection_name,
        embedding=embedding,
        store=qdrant,
        top_k=body.top_k,
    )

    relevance = {q.query_id: q.relevant_chunk_ids for q in test_set.queries}
    metrics = score_retrieval(relevance, retrieval.ranked_lists(), ks=(1, 5, 10))

    return RetrieveResponse(
        results=[
            QueryHitOut(
                query_id=r.query_id,
                ranked_chunk_ids=r.ranked_chunk_ids,
                scores=r.scores,
                latency_ms=r.latency_ms,
            )
            for r in retrieval.results
        ],
        latency=retrieval.latency.as_dict(),
        metrics=metrics,
    )

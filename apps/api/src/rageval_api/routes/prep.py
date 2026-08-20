from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from rageval_api.deps import ArtifactRepoDep, ObjectStoreDep, ProjectRepoDep
from rageval_api.routes.artifacts import _to_out
from rageval_api.schemas import ArtifactOut
from rageval_api.services.artifact_io import load_artifact_model
from rageval_api.services.prep_run import prepare_clean_corpus
from rageval_domain import ArtifactType, RawBundle
from rageval_prep import PrepPipelineId

router = APIRouter(tags=["prep"])


class PrepRequest(BaseModel):
    raw_bundle_id: str
    pipeline: PrepPipelineId = PrepPipelineId.DEFAULT


class PrepResponse(BaseModel):
    artifact: ArtifactOut
    document_count: int
    metrics: dict = Field(default_factory=dict)


@router.post(
    "/projects/{project_id}/prep",
    response_model=PrepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_prep_endpoint(
    project_id: str,
    body: PrepRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> PrepResponse:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        raw_record, bundle = await load_artifact_model(
            artifacts,
            store,
            body.raw_bundle_id,
            RawBundle,
            expected_type=ArtifactType.RAW_BUNDLE.value,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="raw_bundle not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if raw_record.project_id != project_id:
        raise HTTPException(status_code=400, detail="raw_bundle belongs to another project")

    record, metrics = await prepare_clean_corpus(
        project_id=project_id,
        raw_record=raw_record,
        bundle=bundle,
        pipeline=body.pipeline,
        artifacts=artifacts,
        store=store,
    )
    return PrepResponse(
        artifact=await _to_out(record, store, artifacts),
        document_count=int(record.meta.get("document_count") or 0),
        metrics=metrics.as_dict(),
    )

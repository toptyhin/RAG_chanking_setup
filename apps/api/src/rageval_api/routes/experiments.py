from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from rageval_api.deps import ArtifactRepoDep, ExperimentRepoDep, ObjectStoreDep, ProjectRepoDep
from rageval_api.services.experiment_jobs import execute_experiment_job
from rageval_domain import ArtifactType, ExperimentMode
from rageval_metadb_sqlite.experiment_repo import ExperimentRepository
from rageval_orchestrator import CHUNK_LAB_DISCLAIMER, PREP_LAB_DISCLAIMER, expand_grid
from rageval_orchestrator.chunk_lab import DEFAULT_CHUNK_SWEPT
from rageval_orchestrator.prep_lab import DEFAULT_PREP_SWEPT

router = APIRouter(tags=["experiments"])


class ExperimentCreate(BaseModel):
    project_id: str
    evaluates: ExperimentMode = ExperimentMode.RETRIEVAL
    raw_bundle_id: str | None = None
    clean_corpus_id: str | None = None
    chunk_set_id: str | None = None
    test_set_id: str | None = None
    fixed: dict[str, Any] = Field(default_factory=dict)
    swept: dict[str, list[Any]] = Field(default_factory=dict)
    disclaimer: str | None = None


class MetricsRowOut(BaseModel):
    id: int
    point_index: int
    config: dict[str, Any]
    metrics: dict[str, Any]
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    index_run_id: str | None


class ProgressOut(BaseModel):
    done: int = 0
    total: int = 0
    percent: float = 0.0
    current_config: dict[str, Any] | None = None


class ExperimentOut(BaseModel):
    id: str
    project_id: str
    evaluates: str
    start_artifact_type: str
    start_artifact_id: str
    test_set_id: str | None
    fixed: dict[str, Any]
    swept: dict[str, list[Any]]
    status: str
    disclaimer: str | None
    error: str | None
    meta: dict[str, Any]
    progress: ProgressOut | None = None
    pareto: list[dict[str, Any]] = Field(default_factory=list)
    report_object_key: str | None = None
    metrics_rows: list[MetricsRowOut] = Field(default_factory=list)


def _progress_from_meta(meta: dict[str, Any]) -> ProgressOut | None:
    raw = meta.get("progress")
    if not isinstance(raw, dict):
        return None
    return ProgressOut(
        done=int(raw.get("done", 0)),
        total=int(raw.get("total", 0)),
        percent=float(raw.get("percent", 0.0)),
        current_config=raw.get("current_config"),
    )


def _to_out(record) -> ExperimentOut:
    meta = record.meta or {}
    pareto = meta.get("pareto") if isinstance(meta.get("pareto"), list) else []
    return ExperimentOut(
        id=record.id,
        project_id=record.project_id,
        evaluates=record.evaluates,
        start_artifact_type=record.start_artifact_type,
        start_artifact_id=record.start_artifact_id,
        test_set_id=record.test_set_id,
        fixed=record.fixed,
        swept=record.swept,
        status=record.status,
        disclaimer=record.disclaimer,
        error=record.error,
        meta=meta,
        progress=_progress_from_meta(meta),
        pareto=pareto,
        report_object_key=meta.get("report_object_key"),
        metrics_rows=[
            MetricsRowOut(
                id=m.id,
                point_index=m.point_index,
                config=m.config,
                metrics=m.metrics,
                latency_p50_ms=m.latency_p50_ms,
                latency_p95_ms=m.latency_p95_ms,
                index_run_id=m.index_run_id,
            )
            for m in record.metrics_rows
        ],
    )


def _resolve_start(
    body: ExperimentCreate,
) -> tuple[str, str]:
    if body.evaluates == ExperimentMode.RETRIEVAL:
        if not body.chunk_set_id:
            raise HTTPException(status_code=400, detail="chunk_set_id required for retrieval")
        return ArtifactType.CHUNK_SET.value, body.chunk_set_id
    if body.evaluates == ExperimentMode.PREP:
        if not body.raw_bundle_id:
            raise HTTPException(status_code=400, detail="raw_bundle_id required for prep")
        return ArtifactType.RAW_BUNDLE.value, body.raw_bundle_id
    if body.evaluates == ExperimentMode.CHUNK:
        if not body.clean_corpus_id:
            raise HTTPException(status_code=400, detail="clean_corpus_id required for chunk")
        return ArtifactType.CLEAN_CORPUS.value, body.clean_corpus_id
    raise HTTPException(status_code=400, detail=f"unsupported evaluates={body.evaluates}")


async def _validate_create_experiment(
    body: ExperimentCreate,
    *,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
) -> tuple[str, str]:
    if body.evaluates not in {
        ExperimentMode.RETRIEVAL,
        ExperimentMode.PREP,
        ExperimentMode.CHUNK,
    }:
        raise HTTPException(status_code=400, detail="unsupported evaluates mode")
    if await projects.get(body.project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    if not body.test_set_id:
        raise HTTPException(status_code=400, detail="test_set_id is required")

    start_type, start_id = _resolve_start(body)
    start_rec = await artifacts.get(start_id)
    test_rec = await artifacts.get(body.test_set_id)
    if start_rec is None or start_rec.type != start_type:
        raise HTTPException(status_code=404, detail=f"{start_type} not found")
    if test_rec is None or test_rec.type != ArtifactType.TEST_SET.value:
        raise HTTPException(status_code=404, detail="test_set not found")
    if start_rec.project_id != body.project_id or test_rec.project_id != body.project_id:
        raise HTTPException(status_code=400, detail="artifacts belong to another project")
    return start_type, start_id


def _lab_defaults(body: ExperimentCreate) -> tuple[dict[str, Any], dict[str, list[Any]], str | None]:
    fixed = dict(body.fixed)
    swept = dict(body.swept)
    disclaimer = body.disclaimer
    if body.evaluates == ExperimentMode.PREP:
        if not swept and "prep.pipeline" not in fixed:
            swept = dict(DEFAULT_PREP_SWEPT)
        disclaimer = disclaimer or PREP_LAB_DISCLAIMER
    elif body.evaluates == ExperimentMode.CHUNK:
        if not swept and "chunk.size" not in fixed:
            swept = dict(DEFAULT_CHUNK_SWEPT)
        disclaimer = disclaimer or CHUNK_LAB_DISCLAIMER
    return fixed, swept, disclaimer


def _schedule_experiment_job(request: Request, run_id: str) -> None:
    app = request.app
    runner = app.state.task_runner

    async def _job() -> None:
        await execute_experiment_job(
            run_id=run_id,
            session_factory=app.state.session_factory,
            object_store=app.state.object_store,
            qdrant=app.state.qdrant,
            embedding=app.state.embedding_service,
            cache_dir=app.state.settings.cache_dir,
            model_registry=getattr(app.state, "model_registry", None),
        )

    runner.submit(run_id, _job)


@router.get(
    "/projects/{project_id}/experiments",
    response_model=list[ExperimentOut],
)
async def list_project_experiments(
    project_id: str,
    projects: ProjectRepoDep,
    experiments: ExperimentRepoDep,
) -> list[ExperimentOut]:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    runs = await experiments.list_for_project(project_id, with_metrics=False)
    return [_to_out(run) for run in runs]


@router.post(
    "/experiments",
    response_model=ExperimentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_experiment(
    body: ExperimentCreate,
    request: Request,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    experiments: ExperimentRepoDep,
) -> ExperimentOut:
    start_type, start_id = await _validate_create_experiment(
        body, projects=projects, artifacts=artifacts
    )
    fixed, swept, disclaimer = _lab_defaults(body)

    try:
        expand_grid(fixed, swept, max_axes=2)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run = await experiments.create(
        project_id=body.project_id,
        evaluates=body.evaluates.value,
        start_artifact_type=start_type,
        start_artifact_id=start_id,
        test_set_id=body.test_set_id,
        fixed=fixed,
        swept=swept,
        disclaimer=disclaimer,
        meta={"progress": {"done": 0, "total": 0, "percent": 0.0, "current_config": None}},
    )

    await experiments._session.commit()
    _schedule_experiment_job(request, run.id)

    created = await experiments.get(run.id, with_metrics=True)
    if created is None:
        raise HTTPException(status_code=500, detail="run missing after create")
    return _to_out(created)


@router.get("/experiments/{run_id}", response_model=ExperimentOut)
async def get_experiment(
    run_id: str,
    experiments: ExperimentRepoDep,
    wait: bool = False,
    wait_timeout_sec: float = 120.0,
) -> ExperimentOut:
    """Return run status. With ``wait=true``, poll until terminal or timeout."""
    terminal = {"completed", "failed"}
    deadline = asyncio.get_event_loop().time() + wait_timeout_sec
    while True:
        experiments._session.expire_all()
        run = await experiments.get(run_id, with_metrics=True)
        if run is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        if not wait or run.status in terminal:
            return _to_out(run)
        if asyncio.get_event_loop().time() >= deadline:
            return _to_out(run)
        await asyncio.sleep(0.25)


@router.get("/experiments/{run_id}/progress")
async def experiment_progress_sse(run_id: str, request: Request) -> StreamingResponse:
    """SSE stream of progress until the run reaches a terminal status."""

    async def event_gen():
        terminal = {"completed", "failed"}
        factory = request.app.state.session_factory
        last_payload: dict[str, Any] | None = None
        while True:
            if await request.is_disconnected():
                break
            async with factory() as session:
                experiments = ExperimentRepository(session)
                run = await experiments.get(run_id, with_metrics=False)
            if run is None:
                payload = {"error": "not found"}
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                break
            progress = (run.meta or {}).get("progress") or {}
            payload = {
                "run_id": run.id,
                "status": run.status,
                "done": int(progress.get("done", 0)),
                "total": int(progress.get("total", 0)),
                "percent": float(progress.get("percent", 0.0)),
                "current_config": progress.get("current_config"),
            }
            if payload != last_payload:
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                last_payload = payload
            if run.status in terminal:
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/experiments/{run_id}/report")
async def download_report(
    run_id: str,
    experiments: ExperimentRepoDep,
    store: ObjectStoreDep,
) -> Response:
    run = await experiments.get(run_id, with_metrics=False)
    if run is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    key = (run.meta or {}).get("report_object_key")
    if not key:
        raise HTTPException(status_code=404, detail="report not ready")
    try:
        data = store.get(key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="report file missing") from exc
    return Response(
        content=data,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{run_id}-report.html"'},
    )

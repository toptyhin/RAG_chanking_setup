"""Repository for experiment runs and metrics rows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from rageval_domain.ids import new_id
from rageval_metadb_sqlite.models import ExperimentRunRow, MetricsRow


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class MetricsRowRecord:
    id: int
    run_id: str
    point_index: int
    config: dict[str, Any]
    metrics: dict[str, Any]
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    index_run_id: str | None
    created_at: datetime


@dataclass(slots=True)
class ExperimentRunRecord:
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
    created_at: datetime
    updated_at: datetime
    metrics_rows: list[MetricsRowRecord]


def _metrics_from_row(row: MetricsRow) -> MetricsRowRecord:
    return MetricsRowRecord(
        id=row.id,
        run_id=row.run_id,
        point_index=row.point_index,
        config=json.loads(row.config_json or "{}"),
        metrics=json.loads(row.metrics_json or "{}"),
        latency_p50_ms=row.latency_p50_ms,
        latency_p95_ms=row.latency_p95_ms,
        index_run_id=row.index_run_id,
        created_at=row.created_at,
    )


def _run_from_row(row: ExperimentRunRow, *, with_metrics: bool = False) -> ExperimentRunRecord:
    metrics: list[MetricsRowRecord] = []
    if with_metrics:
        metrics = [_metrics_from_row(m) for m in sorted(row.metrics_rows, key=lambda x: x.point_index)]
    return ExperimentRunRecord(
        id=row.id,
        project_id=row.project_id,
        evaluates=row.evaluates,
        start_artifact_type=row.start_artifact_type,
        start_artifact_id=row.start_artifact_id,
        test_set_id=row.test_set_id,
        fixed=json.loads(row.fixed_json or "{}"),
        swept=json.loads(row.swept_json or "{}"),
        status=row.status,
        disclaimer=row.disclaimer,
        error=row.error,
        meta=json.loads(row.meta_json or "{}"),
        created_at=row.created_at,
        updated_at=row.updated_at,
        metrics_rows=metrics,
    )


class ExperimentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: str,
        evaluates: str,
        start_artifact_type: str,
        start_artifact_id: str,
        test_set_id: str | None,
        fixed: dict[str, Any] | None = None,
        swept: dict[str, list[Any]] | None = None,
        disclaimer: str | None = None,
        meta: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> ExperimentRunRecord:
        row = ExperimentRunRow(
            id=run_id or new_id("run"),
            project_id=project_id,
            evaluates=evaluates,
            start_artifact_type=start_artifact_type,
            start_artifact_id=start_artifact_id,
            test_set_id=test_set_id,
            fixed_json=json.dumps(fixed or {}),
            swept_json=json.dumps(swept or {}),
            status="pending",
            disclaimer=disclaimer,
            meta_json=json.dumps(meta or {}),
        )
        self._session.add(row)
        await self._session.flush()
        return _run_from_row(row)

    async def get(self, run_id: str, *, with_metrics: bool = True) -> ExperimentRunRecord | None:
        stmt = select(ExperimentRunRow).where(ExperimentRunRow.id == run_id)
        if with_metrics:
            stmt = stmt.options(selectinload(ExperimentRunRow.metrics_rows))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _run_from_row(row, with_metrics=with_metrics)

    async def list_for_project(
        self,
        project_id: str,
        *,
        with_metrics: bool = False,
    ) -> list[ExperimentRunRecord]:
        stmt = (
            select(ExperimentRunRow)
            .where(ExperimentRunRow.project_id == project_id)
            .order_by(ExperimentRunRow.created_at.desc())
        )
        if with_metrics:
            stmt = stmt.options(selectinload(ExperimentRunRow.metrics_rows))
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [_run_from_row(row, with_metrics=with_metrics) for row in rows]

    async def update_status(
        self,
        run_id: str,
        *,
        status: str,
        error: str | None = None,
        meta: dict[str, Any] | None = None,
        merge_meta: bool = False,
    ) -> ExperimentRunRecord | None:
        row = await self._session.get(ExperimentRunRow, run_id)
        if row is None:
            return None
        row.status = status
        row.error = error
        row.updated_at = _utc_now()
        if meta is not None:
            if merge_meta:
                current = json.loads(row.meta_json or "{}")
                current.update(meta)
                row.meta_json = json.dumps(current)
            else:
                row.meta_json = json.dumps(meta)
        await self._session.flush()
        await self._session.commit()
        return await self.get(run_id, with_metrics=False)

    async def set_disclaimer(self, run_id: str, disclaimer: str) -> None:
        row = await self._session.get(ExperimentRunRow, run_id)
        if row is None:
            return
        row.disclaimer = disclaimer
        row.updated_at = _utc_now()
        await self._session.flush()
        await self._session.commit()

    async def merge_meta(self, run_id: str, patch: dict[str, Any]) -> ExperimentRunRecord | None:
        row = await self._session.get(ExperimentRunRow, run_id)
        if row is None:
            return None
        current = json.loads(row.meta_json or "{}")
        current.update(patch)
        row.meta_json = json.dumps(current)
        row.updated_at = _utc_now()
        await self._session.flush()
        await self._session.commit()
        return await self.get(run_id, with_metrics=False)

    async def set_progress(
        self,
        run_id: str,
        *,
        done: int,
        total: int,
        current_config: dict[str, Any] | None = None,
    ) -> ExperimentRunRecord | None:
        percent = 0.0 if total <= 0 else round(100.0 * done / total, 2)
        progress = {
            "done": done,
            "total": total,
            "percent": percent,
            "current_config": current_config,
        }
        row = await self._session.get(ExperimentRunRow, run_id)
        if row is None:
            return None
        current = json.loads(row.meta_json or "{}")
        if current.get("progress") == progress:
            return _run_from_row(row)
        current["progress"] = progress
        row.meta_json = json.dumps(current)
        row.updated_at = _utc_now()
        await self._session.flush()
        await self._session.commit()
        return _run_from_row(row)

    async def add_metrics_row(
        self,
        *,
        run_id: str,
        point_index: int,
        config: dict[str, Any],
        metrics: dict[str, Any],
        latency_p50_ms: float | None = None,
        latency_p95_ms: float | None = None,
        index_run_id: str | None = None,
        progress_done: int | None = None,
        progress_total: int | None = None,
        progress_config: dict[str, Any] | None = None,
    ) -> MetricsRowRecord:
        row = MetricsRow(
            run_id=run_id,
            point_index=point_index,
            config_json=json.dumps(config),
            metrics_json=json.dumps(metrics),
            latency_p50_ms=latency_p50_ms,
            latency_p95_ms=latency_p95_ms,
            index_run_id=index_run_id,
        )
        self._session.add(row)
        if progress_done is not None and progress_total is not None:
            run_row = await self._session.get(ExperimentRunRow, run_id)
            if run_row is not None:
                meta = json.loads(run_row.meta_json or "{}")
                meta["progress"] = {
                    "done": progress_done,
                    "total": progress_total,
                    "percent": (
                        0.0
                        if progress_total <= 0
                        else round(100.0 * progress_done / progress_total, 2)
                    ),
                    "current_config": progress_config,
                }
                run_row.meta_json = json.dumps(meta)
                run_row.updated_at = _utc_now()
        await self._session.flush()
        await self._session.commit()
        return _metrics_from_row(row)

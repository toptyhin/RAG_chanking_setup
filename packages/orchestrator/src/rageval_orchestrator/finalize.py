"""Post-run Pareto + HTML report persistence."""

from __future__ import annotations

from typing import Any

from rageval_metadb_sqlite.experiment_repo import ExperimentRepository
from rageval_optimize.pareto import points_from_rows, pareto_front
from rageval_report import render_html_report
from rageval_storage_fs import FileSystemObjectStore


def _has_successful_point(rows: list[Any]) -> bool:
    """True when at least one metrics row carries real metrics (not a failure stub)."""
    return any((row.metrics or {}).get("status") != "failed" for row in rows)


async def finalize_run(
    *,
    run_id: str,
    experiments: ExperimentRepository,
    object_store: FileSystemObjectStore,
) -> dict[str, Any]:
    """Attach pareto + report_object_key to run.meta. Idempotent-ish."""
    run = await experiments.get(run_id, with_metrics=True)
    if run is None:
        raise LookupError("experiment run not found")
    if run.status != "completed" or not _has_successful_point(run.metrics_rows):
        # Failed runs (and runs where every point failed) have no quality
        # results to report; keep meta as-is instead of publishing an empty report.
        return dict(run.meta)

    points = points_from_rows(run.metrics_rows)
    front = [p.as_dict() for p in pareto_front(points)]

    metrics_payload = [
        {
            "point_index": m.point_index,
            "config": m.config,
            "metrics": m.metrics,
            "latency_p50_ms": m.latency_p50_ms,
            "latency_p95_ms": m.latency_p95_ms,
            "index_run_id": m.index_run_id,
        }
        for m in run.metrics_rows
    ]
    html = render_html_report(
        run_id=run.id,
        project_id=run.project_id,
        evaluates=run.evaluates,
        status=run.status,
        disclaimer=run.disclaimer,
        metrics_rows=metrics_payload,
        pareto=front,
        meta=run.meta,
    )
    report_key = f"{run.id}/report.html"
    object_store.put(report_key, html.encode("utf-8"))

    patch = {
        "pareto": front,
        "report_object_key": report_key,
    }
    await experiments.merge_meta(run_id, patch)
    return {**run.meta, **patch}

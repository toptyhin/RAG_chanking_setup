"""Jinja2 HTML report for an experiment run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html_report(
    *,
    run_id: str,
    project_id: str,
    evaluates: str,
    status: str,
    disclaimer: str | None,
    metrics_rows: list[dict[str, Any]],
    pareto: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")
    return template.render(
        run_id=run_id,
        project_id=project_id,
        evaluates=evaluates,
        status=status,
        disclaimer=disclaimer,
        metrics_rows=metrics_rows,
        pareto=pareto,
        meta=meta or {},
    )

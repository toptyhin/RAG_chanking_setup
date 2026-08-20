from __future__ import annotations

from rageval_report import render_html_report


def test_render_html_contains_tables() -> None:
    html = render_html_report(
        run_id="run_1",
        project_id="proj_1",
        evaluates="retrieval",
        status="completed",
        disclaimer="test disclaimer",
        metrics_rows=[
            {
                "point_index": 0,
                "config": {"retrieval.top_k": 5},
                "metrics": {"recall@5": 1.0},
                "latency_p50_ms": 1.0,
                "latency_p95_ms": 2.0,
            }
        ],
        pareto=[
            {
                "point_index": 0,
                "recall": 1.0,
                "latency_p95_ms": 2.0,
                "index_size_mb": 0.1,
                "config": {"retrieval.top_k": 5},
            }
        ],
    )
    assert "run_1" in html
    assert "test disclaimer" in html
    assert "Pareto" in html
    assert "recall@5" in html or "1.0" in html

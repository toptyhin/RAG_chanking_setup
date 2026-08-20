"""create experiment_runs and metrics_rows

Revision ID: 003
Revises: 002
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("evaluates", sa.String(length=64), nullable=False),
        sa.Column("start_artifact_type", sa.String(length=64), nullable=False),
        sa.Column("start_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("test_set_id", sa.String(length=64), nullable=True),
        sa.Column("fixed_json", sa.Text(), nullable=False),
        sa.Column("swept_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_runs_project_id", "experiment_runs", ["project_id"])

    op.create_table(
        "metrics_rows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("point_index", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("latency_p50_ms", sa.Float(), nullable=True),
        sa.Column("latency_p95_ms", sa.Float(), nullable=True),
        sa.Column("index_run_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["experiment_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metrics_rows_run_id", "metrics_rows", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_metrics_rows_run_id", table_name="metrics_rows")
    op.drop_table("metrics_rows")
    op.drop_index("ix_experiment_runs_project_id", table_name="experiment_runs")
    op.drop_table("experiment_runs")

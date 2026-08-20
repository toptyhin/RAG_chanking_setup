"""Experiment run repository tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rageval_metadb_sqlite import (
    ExperimentRepository,
    create_engine,
    create_session_factory,
    init_db,
)
from rageval_metadb_sqlite.repositories import ProjectRepository


@pytest.fixture
async def session_factory(tmp_path: Path):
    db_path = tmp_path / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_engine(url)
    await init_db(engine)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def test_create_pending_run(session_factory) -> None:
    async with session_factory() as session:
        projects = ProjectRepository(session)
        project = await projects.create(name="E")
        experiments = ExperimentRepository(session)
        run = await experiments.create(
            project_id=project.id,
            evaluates="retrieval",
            start_artifact_type="chunk_set",
            start_artifact_id="chunks_1",
            test_set_id="test_1",
            fixed={},
            swept={"retrieval.top_k": [5, 10]},
        )
        await session.commit()
        assert run.status == "pending"
        assert run.id.startswith("run_")

    async with session_factory() as session:
        experiments = ExperimentRepository(session)
        loaded = await experiments.get(run.id)
        assert loaded is not None
        assert loaded.status == "pending"
        assert loaded.swept["retrieval.top_k"] == [5, 10]


async def test_list_for_project(session_factory) -> None:
    async with session_factory() as session:
        projects = ProjectRepository(session)
        project = await projects.create(name="List")
        other = await projects.create(name="Other")
        experiments = ExperimentRepository(session)
        first = await experiments.create(
            project_id=project.id,
            evaluates="retrieval",
            start_artifact_type="chunk_set",
            start_artifact_id="chunks_a",
            test_set_id="test_a",
        )
        second = await experiments.create(
            project_id=project.id,
            evaluates="retrieval",
            start_artifact_type="chunk_set",
            start_artifact_id="chunks_b",
            test_set_id="test_b",
        )
        await experiments.create(
            project_id=other.id,
            evaluates="retrieval",
            start_artifact_type="chunk_set",
            start_artifact_id="chunks_x",
            test_set_id="test_x",
        )
        await session.commit()

    async with session_factory() as session:
        experiments = ExperimentRepository(session)
        listed = await experiments.list_for_project(project.id)
        ids = [r.id for r in listed]
        assert second.id in ids
        assert first.id in ids
        assert len(ids) == 2
        assert ids[0] == second.id


async def test_metrics_and_progress_commit_together(session_factory) -> None:
    async with session_factory() as session:
        project = await ProjectRepository(session).create(name="Progress")
        experiments = ExperimentRepository(session)
        run = await experiments.create(
            project_id=project.id,
            evaluates="retrieval",
            start_artifact_type="chunk_set",
            start_artifact_id="chunks_progress",
            test_set_id="test_progress",
        )
        await session.commit()

        await experiments.add_metrics_row(
            run_id=run.id,
            point_index=0,
            config={"retrieval.top_k": 5},
            metrics={"recall@5": 1.0},
            progress_done=1,
            progress_total=2,
            progress_config={"retrieval.top_k": 10},
        )

    async with session_factory() as session:
        loaded = await ExperimentRepository(session).get(run.id)
        assert loaded is not None
        assert len(loaded.metrics_rows) == 1
        assert loaded.meta["progress"] == {
            "done": 1,
            "total": 2,
            "percent": 50.0,
            "current_config": {"retrieval.top_k": 10},
        }

"""MetaDB project repository tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rageval_metadb_sqlite import (
    ProjectRepository,
    create_engine,
    create_session_factory,
    init_db,
)


@pytest.fixture
async def session_factory(tmp_path: Path):
    db_path = tmp_path / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_engine(url)
    await init_db(engine)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def test_create_and_get_project(session_factory) -> None:
    async with session_factory() as session:
        repo = ProjectRepository(session)
        created = await repo.create(name="Demo", description="phase B")
        await session.commit()
        project_id = created.id

    async with session_factory() as session:
        repo = ProjectRepository(session)
        loaded = await repo.get(project_id)
        assert loaded is not None
        assert loaded.name == "Demo"
        listed = await repo.list()
        assert any(p.id == project_id for p in listed)

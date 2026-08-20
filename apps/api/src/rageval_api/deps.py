"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rageval_domain.settings import Settings
from rageval_metadb_sqlite.experiment_repo import ExperimentRepository
from rageval_metadb_sqlite.repositories import ArtifactRepository, ProjectRepository
from rageval_storage_fs import FileSystemObjectStore


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


def get_object_store(request: Request) -> FileSystemObjectStore:
    return request.app.state.object_store


async def get_session(
    factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_project_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectRepository:
    return ProjectRepository(session)


async def get_artifact_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArtifactRepository:
    return ArtifactRepository(session)


async def get_experiment_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExperimentRepository:
    return ExperimentRepository(session)


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
ObjectStoreDep = Annotated[FileSystemObjectStore, Depends(get_object_store)]
ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repo)]
ArtifactRepoDep = Annotated[ArtifactRepository, Depends(get_artifact_repo)]
ExperimentRepoDep = Annotated[ExperimentRepository, Depends(get_experiment_repo)]

"""Repositories for projects and artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rageval_domain.ids import new_id
from rageval_metadb_sqlite.models import ArtifactRow, ProjectRow


@dataclass(slots=True)
class Project:
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ArtifactRecord:
    id: str
    project_id: str
    type: str
    parent_ids: list[str]
    content_hash: str | None
    object_key: str | None
    meta: dict[str, Any]
    created_at: datetime


def _project_from_row(row: ProjectRow) -> Project:
    return Project(
        id=row.id,
        name=row.name,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _artifact_from_row(row: ArtifactRow) -> ArtifactRecord:
    return ArtifactRecord(
        id=row.id,
        project_id=row.project_id,
        type=row.type,
        parent_ids=json.loads(row.parent_ids_json or "[]"),
        content_hash=row.content_hash,
        object_key=row.object_key,
        meta=json.loads(row.meta_json or "{}"),
        created_at=row.created_at,
    )


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, description: str | None = None) -> Project:
        row = ProjectRow(id=new_id("proj"), name=name, description=description)
        self._session.add(row)
        await self._session.flush()
        return _project_from_row(row)

    async def get(self, project_id: str) -> Project | None:
        row = await self._session.get(ProjectRow, project_id)
        return _project_from_row(row) if row else None

    async def list(self) -> list[Project]:
        result = await self._session.execute(
            select(ProjectRow).order_by(ProjectRow.created_at.desc())
        )
        return [_project_from_row(r) for r in result.scalars().all()]


class ArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        artifact_id: str,
        project_id: str,
        artifact_type: str,
        parent_ids: list[str] | None = None,
        content_hash: str | None = None,
        object_key: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        row = ArtifactRow(
            id=artifact_id,
            project_id=project_id,
            type=artifact_type,
            parent_ids_json=json.dumps(parent_ids or []),
            content_hash=content_hash,
            object_key=object_key,
            meta_json=json.dumps(meta or {}),
        )
        self._session.add(row)
        await self._session.flush()
        return _artifact_from_row(row)

    async def get(self, artifact_id: str) -> ArtifactRecord | None:
        row = await self._session.get(ArtifactRow, artifact_id)
        return _artifact_from_row(row) if row else None

    async def list_for_project(
        self,
        project_id: str,
        *,
        artifact_type: str | None = None,
    ) -> list[ArtifactRecord]:
        stmt = select(ArtifactRow).where(ArtifactRow.project_id == project_id)
        if artifact_type is not None:
            stmt = stmt.where(ArtifactRow.type == artifact_type)
        stmt = stmt.order_by(ArtifactRow.created_at.desc())
        result = await self._session.execute(stmt)
        return [_artifact_from_row(r) for r in result.scalars().all()]

    async def delete(self, artifact_id: str) -> bool:
        row = await self._session.get(ArtifactRow, artifact_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    async def update_content(
        self,
        artifact_id: str,
        *,
        content_hash: str,
        object_key: str | None = None,
        meta: dict[str, Any] | None = None,
        merge_meta: bool = True,
    ) -> ArtifactRecord | None:
        """Overwrite blob metadata for an existing artifact (e.g. relevance review)."""
        row = await self._session.get(ArtifactRow, artifact_id)
        if row is None:
            return None
        row.content_hash = content_hash
        if object_key is not None:
            row.object_key = object_key
        if meta is not None:
            if merge_meta:
                current = json.loads(row.meta_json or "{}")
                current.update(meta)
                row.meta_json = json.dumps(current)
            else:
                row.meta_json = json.dumps(meta)
        await self._session.flush()
        await self._session.commit()
        return _artifact_from_row(row)

    async def list_dependents(
        self,
        artifact_id: str,
        *,
        project_id: str | None = None,
    ) -> list[ArtifactRecord]:
        """Artifacts that list `artifact_id` in parent_ids."""
        stmt = select(ArtifactRow)
        if project_id is not None:
            stmt = stmt.where(ArtifactRow.project_id == project_id)
        result = await self._session.execute(stmt)
        dependents: list[ArtifactRecord] = []
        for row in result.scalars().all():
            parents = json.loads(row.parent_ids_json or "[]")
            if artifact_id in parents:
                dependents.append(_artifact_from_row(row))
        return dependents

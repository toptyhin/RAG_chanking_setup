"""HTTP request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ArtifactOut(BaseModel):
    id: str
    project_id: str
    type: str
    parent_ids: list[str]
    content_hash: str | None
    object_key: str | None
    meta: dict[str, Any]
    created_at: datetime


class RawBundleUploadResponse(BaseModel):
    artifact: ArtifactOut
    files_stored: int
    clean_corpus: ArtifactOut
    document_count: int = 0
    prep_metrics: dict[str, Any] = Field(default_factory=dict)


class ArtifactImportRequest(BaseModel):
    source_project_id: str = Field(min_length=1)
    artifact_ids: list[str] = Field(min_length=1)
    include_parents: bool = True


class ArtifactImportResponse(BaseModel):
    artifacts: list[ArtifactOut]
    id_map: dict[str, str]


class ArtifactDeleteResponse(BaseModel):
    deleted: list[str]

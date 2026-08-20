"""Artifact and experiment domain models (pure Pydantic, no I/O)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from rageval_domain.ids import new_id


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactType(StrEnum):
    RAW_BUNDLE = "raw_bundle"
    CLEAN_CORPUS = "clean_corpus"
    CHUNK_SET = "chunk_set"
    TEST_SET = "test_set"
    INDEX_RUN = "index_run"
    EXPERIMENT_RUN = "experiment_run"
    EVAL_REPORT = "eval_report"


class ExperimentMode(StrEnum):
    PREP = "prep"
    CHUNK = "chunk"
    RETRIEVAL = "retrieval"
    E2E_PRESETS = "e2e_presets"


class ArtifactRef(BaseModel):
    """Lightweight pointer used inside parent/child links."""

    type: ArtifactType
    id: str


class RawFileRef(BaseModel):
    path: str
    original_name: str
    content_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None


class RawBundle(BaseModel):
    id: str = Field(default_factory=lambda: new_id("raw"))
    project_id: str
    artifact_type: ArtifactType = ArtifactType.RAW_BUNDLE
    files: list[RawFileRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_type")
    @classmethod
    def _type_must_match(cls, value: ArtifactType) -> ArtifactType:
        if value != ArtifactType.RAW_BUNDLE:
            raise ValueError("RawBundle.artifact_type must be raw_bundle")
        return value


class CleanDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: new_id("doc"))
    text: str
    source_path: str | None = None
    page: int | None = None
    language: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CleanCorpus(BaseModel):
    id: str = Field(default_factory=lambda: new_id("clean"))
    project_id: str
    artifact_type: ArtifactType = ArtifactType.CLEAN_CORPUS
    parent_ids: list[str] = Field(default_factory=list)
    prep_pipeline_id: str | None = None
    documents: list[CleanDocument] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_type")
    @classmethod
    def _type_must_match(cls, value: ArtifactType) -> ArtifactType:
        if value != ArtifactType.CLEAN_CORPUS:
            raise ValueError("CleanCorpus.artifact_type must be clean_corpus")
        return value


class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: new_id("chunk"))
    doc_id: str
    text: str
    start_char: int | None = None
    end_char: int | None = None
    parent_chunk_id: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ChunkSet(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chunks"))
    project_id: str
    artifact_type: ArtifactType = ArtifactType.CHUNK_SET
    parent_ids: list[str] = Field(default_factory=list)
    chunk_pipeline_id: str | None = None
    chunks: list[Chunk] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_type")
    @classmethod
    def _type_must_match(cls, value: ArtifactType) -> ArtifactType:
        if value != ArtifactType.CHUNK_SET:
            raise ValueError("ChunkSet.artifact_type must be chunk_set")
        return value


class TestQuery(BaseModel):
    # Not a pytest test class
    __test__ = False

    query_id: str = Field(default_factory=lambda: new_id("q"))
    text: str
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    relevant_doc_ids: list[str] = Field(default_factory=list)
    # Optional character spans in clean docs: [{"doc_id", "start", "end"}]
    relevant_spans: list[dict[str, Any]] = Field(default_factory=list)
    # Graded relevance: chunk_id → gain (e.g. primary=2, secondary=1). Binary if empty.
    relevance_grades: dict[str, float] = Field(default_factory=dict)
    expected_answer: str | None = None
    source_quote: str | None = None
    query_type: str | None = None
    # How the question entered the evaluator: synthetic | manual | imported | unknown.
    source: str = "unknown"
    reviewed: bool = False
    # Label provenance: "auto" | "verified" (also mirrored in meta.label_status).
    label_status: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class TestSet(BaseModel):
    # Not a pytest test class
    __test__ = False

    id: str = Field(default_factory=lambda: new_id("test"))
    project_id: str
    artifact_type: ArtifactType = ArtifactType.TEST_SET
    parent_ids: list[str] = Field(default_factory=list)
    queries: list[TestQuery] = Field(default_factory=list)
    source: str = "unknown"
    reviewed: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_type")
    @classmethod
    def _type_must_match(cls, value: ArtifactType) -> ArtifactType:
        if value != ArtifactType.TEST_SET:
            raise ValueError("TestSet.artifact_type must be test_set")
        return value


class IndexRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("index"))
    project_id: str
    artifact_type: ArtifactType = ArtifactType.INDEX_RUN
    parent_ids: list[str] = Field(default_factory=list)
    chunk_set_id: str
    collection_name: str
    embedding_model: str
    dimension: int
    quantization: dict[str, Any] | None = None
    hnsw: dict[str, Any] = Field(default_factory=dict)
    build_time_sec: float | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_type")
    @classmethod
    def _type_must_match(cls, value: ArtifactType) -> ArtifactType:
        if value != ArtifactType.INDEX_RUN:
            raise ValueError("IndexRun.artifact_type must be index_run")
        return value


class ExperimentRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    project_id: str
    artifact_type: ArtifactType = ArtifactType.EXPERIMENT_RUN
    evaluates: ExperimentMode
    start_artifact: ArtifactRef
    test_set_id: str | None = None
    fixed: dict[str, Any] = Field(default_factory=dict)
    swept: dict[str, list[Any]] = Field(default_factory=dict)
    status: str = "pending"
    disclaimer: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_type")
    @classmethod
    def _type_must_match(cls, value: ArtifactType) -> ArtifactType:
        if value != ArtifactType.EXPERIMENT_RUN:
            raise ValueError("ExperimentRun.artifact_type must be experiment_run")
        return value

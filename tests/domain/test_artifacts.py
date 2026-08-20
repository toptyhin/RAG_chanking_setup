"""Unit tests for domain artifact models (JSON round-trip)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from rageval_domain import (
    ArtifactType,
    Chunk,
    ChunkSet,
    CleanCorpus,
    CleanDocument,
    ExperimentMode,
    ExperimentRun,
    IndexRun,
    RawBundle,
    RawFileRef,
    TestQuery,
    TestSet,
    new_id,
)
from rageval_domain.artifacts import ArtifactRef


def test_new_id_has_prefix_and_hex() -> None:
    value = new_id("raw")
    assert value.startswith("raw_")
    assert len(value) == len("raw_") + 32


def test_raw_bundle_json_roundtrip() -> None:
    bundle = RawBundle(
        project_id="proj_1",
        files=[
            RawFileRef(
                path="objects/raw_abc/a.txt",
                original_name="a.txt",
                content_type="text/plain",
                size_bytes=12,
            )
        ],
    )
    payload = json.loads(bundle.model_dump_json())
    restored = RawBundle.model_validate(payload)
    assert restored.artifact_type == ArtifactType.RAW_BUNDLE
    assert restored.files[0].original_name == "a.txt"
    assert restored.id.startswith("raw_")


def test_clean_corpus_and_chunk_set_from_json() -> None:
    clean_json = {
        "id": "clean_demo",
        "project_id": "proj_1",
        "parent_ids": ["raw_demo"],
        "prep_pipeline_id": "prep_plaintext",
        "documents": [
            {
                "doc_id": "doc_1",
                "text": "Hello world",
                "source_path": "a.txt",
            }
        ],
    }
    clean = CleanCorpus.model_validate(clean_json)
    assert clean.documents[0].text == "Hello world"

    chunks = ChunkSet(
        project_id="proj_1",
        parent_ids=[clean.id],
        chunk_pipeline_id="reference_fixed",
        chunks=[
            Chunk(chunk_id="chunk_1", doc_id="doc_1", text="Hello world", start_char=0, end_char=11)
        ],
    )
    assert chunks.artifact_type == ArtifactType.CHUNK_SET
    assert chunks.chunks[0].chunk_id == "chunk_1"


def test_testset_index_experiment_json() -> None:
    test_set = TestSet.model_validate(
        {
            "id": "test_1",
            "project_id": "proj_1",
            "queries": [
                {
                    "query_id": "q_1",
                    "text": "What is hello?",
                    "relevant_chunk_ids": ["chunk_1"],
                }
            ],
        }
    )
    assert test_set.queries[0].relevant_chunk_ids == ["chunk_1"]

    index = IndexRun(
        project_id="proj_1",
        chunk_set_id="chunks_1",
        collection_name="col_1",
        embedding_model="demo-model",
        dimension=384,
        quantization=None,
        hnsw={"m": 16},
    )
    assert index.artifact_type == ArtifactType.INDEX_RUN

    run = ExperimentRun(
        project_id="proj_1",
        evaluates=ExperimentMode.RETRIEVAL,
        start_artifact=ArtifactRef(type=ArtifactType.CHUNK_SET, id="chunks_1"),
        test_set_id=test_set.id,
        fixed={"embedding.model": "demo-model"},
        swept={"retrieval.top_k": [5, 10]},
    )
    payload = json.loads(run.model_dump_json())
    restored = ExperimentRun.model_validate(payload)
    assert restored.evaluates == ExperimentMode.RETRIEVAL
    assert restored.swept["retrieval.top_k"] == [5, 10]


def test_wrong_artifact_type_rejected() -> None:
    with pytest.raises(ValidationError):
        CleanCorpus.model_validate(
            {
                "project_id": "proj_1",
                "artifact_type": "chunk_set",
                "documents": [CleanDocument(text="x").model_dump()],
            }
        )


def test_clean_document_defaults() -> None:
    doc = CleanDocument(text="only text")
    assert doc.doc_id.startswith("doc_")
    assert doc.meta == {}

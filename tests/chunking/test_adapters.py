"""Library chunker adapter tests."""

from __future__ import annotations

import importlib.util

import pytest

from rageval_chunking import (
    ChunkletOptions,
    ReferenceOptions,
    SemchunkOptions,
    chunk_corpus,
    clear_registry_cache,
    list_providers,
)
from rageval_domain import CleanCorpus, CleanDocument

HAS_SEMCHUNK = importlib.util.find_spec("semchunk") is not None
HAS_CHUNKLET = importlib.util.find_spec("chunklet") is not None


def _en_corpus() -> CleanCorpus:
    return CleanCorpus(
        project_id="proj_1",
        documents=[
            CleanDocument(
                doc_id="doc_en",
                text=(
                    "Cats are wonderful pets. Dogs are loyal companions. "
                    "Robots use artificial intelligence. Flying in space needs AI."
                ),
            )
        ],
    )


def _ru_corpus() -> CleanCorpus:
    return CleanCorpus(
        project_id="proj_1",
        documents=[
            CleanDocument(
                doc_id="doc_ru",
                text=(
                    "Кошки — замечательные питомцы. Собаки верные компаньоны. "
                    "Роботы используют искусственный интеллект. Полёты в космос требуют ИИ."
                ),
            )
        ],
    )


def _code_corpus() -> CleanCorpus:
    return CleanCorpus(
        project_id="proj_1",
        documents=[
            CleanDocument(
                doc_id="doc_py",
                text="def a():\n    return 1\n\ndef b():\n    return 2\n",
            )
        ],
    )


@pytest.mark.skipif(not HAS_SEMCHUNK, reason="semchunk not installed")
def test_semchunk_adapter() -> None:
    clear_registry_cache()
    result = chunk_corpus(
        _en_corpus(),
        SemchunkOptions(chunk_size=8, overlap=0, token_counter="words"),
    )
    assert result.chunk_pipeline_id == "semchunk"
    assert len(result.chunks) >= 2
    assert all(c.start_char is not None for c in result.chunks)


@pytest.mark.skipif(not HAS_CHUNKLET, reason="chunklet not installed")
def test_chunklet_document_adapter() -> None:
    clear_registry_cache()
    result = chunk_corpus(
        _ru_corpus(),
        ChunkletOptions(mode="document", lang="ru", max_sentences=2),
    )
    assert result.chunk_pipeline_id == "chunklet_document"
    assert len(result.chunks) >= 1


@pytest.mark.skipif(not HAS_CHUNKLET, reason="chunklet not installed")
def test_chunklet_code_adapter() -> None:
    clear_registry_cache()
    result = chunk_corpus(
        _code_corpus(),
        ChunkletOptions(mode="code", max_functions=1),
    )
    assert result.chunk_pipeline_id == "chunklet_code"
    assert len(result.chunks) >= 2


def test_list_providers_reference_last_and_available() -> None:
    providers = list_providers()
    assert providers[-1].id == "reference_fixed"
    assert providers[-1].available is True
    clear_registry_cache()
    result = chunk_corpus(_en_corpus(), ReferenceOptions(size=40, overlap=5))
    assert result.chunk_pipeline_id == "reference_fixed"

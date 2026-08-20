"""Domain models and settings for rageval (no I/O adapters)."""

from rageval_domain.artifacts import (
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
)
from rageval_domain.ids import content_id, new_id
from rageval_domain.query_type import normalize_query_type, resolve_query_type
from rageval_domain.settings import Settings, get_settings

__version__ = "0.1.0"

__all__ = [
    "ArtifactType",
    "Chunk",
    "ChunkSet",
    "CleanCorpus",
    "CleanDocument",
    "ExperimentMode",
    "ExperimentRun",
    "IndexRun",
    "RawBundle",
    "RawFileRef",
    "Settings",
    "TestQuery",
    "TestSet",
    "__version__",
    "content_id",
    "get_settings",
    "new_id",
    "normalize_query_type",
    "resolve_query_type",
]

"""Chunker protocol."""

from __future__ import annotations

from typing import Protocol

from rageval_domain import ChunkSet, CleanCorpus

from rageval_chunking.options import ChunkerOptions


class Chunker(Protocol):
    def chunk_corpus(self, corpus: CleanCorpus, options: ChunkerOptions) -> ChunkSet:
        """Chunk every document in *corpus* according to *options*."""
        ...

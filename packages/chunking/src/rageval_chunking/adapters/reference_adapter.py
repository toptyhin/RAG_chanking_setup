"""Reference fixed-size chunker adapter."""

from __future__ import annotations

from rageval_domain import ChunkSet, CleanCorpus

from rageval_chunking.options import ChunkerOptions, ReferenceOptions
from rageval_chunking.reference import chunk_fixed_size


class ReferenceChunker:
    def chunk_corpus(self, corpus: CleanCorpus, options: ChunkerOptions) -> ChunkSet:
        if not isinstance(options, ReferenceOptions):
            raise TypeError(f"ReferenceChunker expects ReferenceOptions, got {type(options)}")
        return chunk_fixed_size(corpus, size=options.size, overlap=options.overlap)

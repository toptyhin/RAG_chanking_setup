"""Semchunk adapter (no Isaacus AI)."""

from __future__ import annotations

from rageval_domain import Chunk, ChunkSet, CleanCorpus

from rageval_chunking.adapters._common import build_chunk_set, make_chunk
from rageval_chunking.options import ChunkerOptions, SemchunkOptions
from rageval_chunking.token_counters import resolve_token_counter

PIPELINE_ID = "semchunk"


class SemchunkChunker:
    def chunk_corpus(self, corpus: CleanCorpus, options: ChunkerOptions) -> ChunkSet:
        if not isinstance(options, SemchunkOptions):
            raise TypeError(f"SemchunkChunker expects SemchunkOptions, got {type(options)}")

        import semchunk

        counter = resolve_token_counter(options.token_counter)
        chunker = semchunk.chunkerify(counter, options.chunk_size)

        chunks: list[Chunk] = []
        for doc in corpus.documents:
            text = doc.text or ""
            if not text.strip():
                continue
            result = chunker(text, offsets=True, overlap=options.overlap)
            pieces, offsets = result
            for index, (piece, (start, end)) in enumerate(zip(pieces, offsets, strict=True)):
                if not piece.strip():
                    continue
                chunks.append(
                    make_chunk(
                        doc_id=doc.doc_id,
                        text=piece,
                        index=index,
                        pipeline_id=PIPELINE_ID,
                        start=start,
                        end=end,
                    )
                )

        return build_chunk_set(
            corpus,
            pipeline_id=PIPELINE_ID,
            chunks=chunks,
            pipeline_meta=options.model_dump(),
        )

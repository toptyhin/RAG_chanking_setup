"""Chunklet DocumentChunker / CodeChunker adapter."""

from __future__ import annotations

from typing import Any

from rageval_domain import Chunk, ChunkSet, CleanCorpus

from rageval_chunking.adapters._common import build_chunk_set, make_chunk
from rageval_chunking.options import ChunkerOptions, ChunkletOptions
from rageval_chunking.token_counters import resolve_token_counter


def _pipeline_id(mode: str) -> str:
    return f"chunklet_{mode}"


def _span_from_meta(meta: dict[str, Any]) -> tuple[int | None, int | None]:
    span = meta.get("span")
    if isinstance(span, (list, tuple)) and len(span) == 2:
        return int(span[0]), int(span[1])
    return None, None


class ChunkletChunker:
    def chunk_corpus(self, corpus: CleanCorpus, options: ChunkerOptions) -> ChunkSet:
        if not isinstance(options, ChunkletOptions):
            raise TypeError(f"ChunkletChunker expects ChunkletOptions, got {type(options)}")

        counter = None
        if options.max_tokens is not None:
            counter = resolve_token_counter(options.token_counter)

        pipeline_id = _pipeline_id(options.mode)
        if options.mode == "code":
            chunks = _chunk_code_docs(corpus, options, counter, pipeline_id)
        else:
            chunks = _chunk_document_docs(corpus, options, counter, pipeline_id)

        return build_chunk_set(
            corpus,
            pipeline_id=pipeline_id,
            chunks=chunks,
            pipeline_meta=options.model_dump(),
        )


def _append_chunklet_items(
    *,
    chunks: list[Chunk],
    doc_id: str,
    raw: list[Any],
    pipeline_id: str,
) -> None:
    for index, item in enumerate(raw):
        meta = dict(item.metadata) if item.metadata else {}
        start, end = _span_from_meta(meta)
        chunks.append(
            make_chunk(
                doc_id=doc_id,
                text=item.content,
                index=index,
                pipeline_id=pipeline_id,
                start=start,
                end=end,
                extra_meta={"chunklet": meta},
            )
        )


def _chunk_code_docs(
    corpus: CleanCorpus,
    options: ChunkletOptions,
    counter: Any,
    pipeline_id: str,
) -> list[Chunk]:
    from chunklet import CodeChunker

    code_chunker = CodeChunker(token_counter=counter)
    chunks: list[Chunk] = []
    for doc in corpus.documents:
        text = doc.text or ""
        if not text.strip():
            continue
        raw = code_chunker.chunk_text(
            text,
            max_tokens=options.max_tokens,
            max_lines=options.max_lines,
            max_functions=options.max_functions,
            token_counter=counter,
            include_comments=options.include_comments,
            docstring_mode=options.docstring_mode,
            strict=options.strict,
        )
        _append_chunklet_items(
            chunks=chunks, doc_id=doc.doc_id, raw=raw, pipeline_id=pipeline_id
        )
    return chunks


def _chunk_document_docs(
    corpus: CleanCorpus,
    options: ChunkletOptions,
    counter: Any,
    pipeline_id: str,
) -> list[Chunk]:
    from chunklet import DocumentChunker

    doc_chunker = DocumentChunker(token_counter=counter)
    chunks: list[Chunk] = []
    for doc in corpus.documents:
        text = doc.text or ""
        if not text.strip():
            continue
        raw = doc_chunker.chunk_text(
            text,
            lang=options.lang,
            max_tokens=options.max_tokens,
            max_sentences=options.max_sentences,
            max_section_breaks=options.max_section_breaks,
            overlap_percent=options.overlap_percent,
            offset=options.offset,
            token_counter=counter,
        )
        _append_chunklet_items(
            chunks=chunks, doc_id=doc.doc_id, raw=raw, pipeline_id=pipeline_id
        )
    return chunks

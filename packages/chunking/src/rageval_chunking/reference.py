"""Reference fixed-size chunker for Retrieval Lab."""

from __future__ import annotations

from rageval_domain import Chunk, ChunkSet, CleanCorpus, content_id

from rageval_chunking.ids import stable_chunk_id

REFERENCE_PIPELINE_ID = "reference_fixed"


def chunk_fixed_size(
    corpus: CleanCorpus,
    *,
    size: int = 512,
    overlap: int = 64,
) -> ChunkSet:
    if size <= 0:
        raise ValueError("size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    step = size - overlap
    chunks: list[Chunk] = []

    for doc in corpus.documents:
        text = doc.text
        if not text:
            continue
        start = 0
        index = 0
        while start < len(text):
            end = min(start + size, len(text))
            piece = text[start:end]
            if piece.strip():
                chunks.append(
                    Chunk(
                        chunk_id=stable_chunk_id(doc.doc_id, start, end),
                        doc_id=doc.doc_id,
                        text=piece,
                        start_char=start,
                        end_char=end,
                        meta={"index": index, "pipeline": REFERENCE_PIPELINE_ID},
                    )
                )
                index += 1
            if end >= len(text):
                break
            start += step

    return ChunkSet(
        id=content_id(
            "chunks",
            corpus.project_id,
            corpus.id,
            REFERENCE_PIPELINE_ID,
            {"size": size, "overlap": overlap},
            [chunk.model_dump(mode="json") for chunk in chunks],
        ),
        project_id=corpus.project_id,
        parent_ids=[corpus.id],
        chunk_pipeline_id=REFERENCE_PIPELINE_ID,
        chunks=chunks,
        meta={
            "chunk_pipeline": {
                "id": REFERENCE_PIPELINE_ID,
                "size": size,
                "overlap": overlap,
            }
        },
    )

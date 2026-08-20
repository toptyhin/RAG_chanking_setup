"""Prep pipeline orchestration over a RawBundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable

from rageval_domain import CleanCorpus, CleanDocument, RawBundle, RawFileRef, content_id
from rageval_prep.pdf import extract_pdf, extract_pdf_clean, is_pdf_name
from rageval_prep.plaintext import extract_plaintext, is_plaintext_name


class PrepPipelineId(StrEnum):
    PLAINTEXT = "plaintext"
    DEFAULT = "default"  # plaintext + pdf
    PDF_CLEAN = "pdf_clean"  # plaintext + aggressively cleaned pdf


@dataclass
class PrepMetrics:
    files_seen: int = 0
    files_parsed: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    documents_created: int = 0
    broken_files: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "files_seen": self.files_seen,
            "files_parsed": self.files_parsed,
            "files_skipped": self.files_skipped,
            "files_failed": self.files_failed,
            "documents_created": self.documents_created,
            "broken_files": list(self.broken_files),
        }


FileLoader = Callable[[str], bytes]


def run_prep(
    bundle: RawBundle,
    *,
    load_file: FileLoader,
    pipeline_id: PrepPipelineId | str = PrepPipelineId.DEFAULT,
) -> tuple[CleanCorpus, PrepMetrics]:
    pipeline = PrepPipelineId(pipeline_id)
    metrics = PrepMetrics()
    documents: list[CleanDocument] = []

    for ref in bundle.files:
        metrics.files_seen += 1
        try:
            docs = _extract_file(ref, load_file=load_file, pipeline=pipeline)
        except Exception as exc:  # noqa: BLE001 — collect prep failures
            metrics.files_failed += 1
            metrics.broken_files.append(f"{ref.original_name}: {exc}")
            continue

        if docs is None:
            metrics.files_skipped += 1
            continue

        metrics.files_parsed += 1
        documents.extend(docs)

    metrics.documents_created = len(documents)
    corpus = CleanCorpus(
        id=content_id(
            "clean",
            bundle.project_id,
            pipeline.value,
            [
                {
                    "doc_id": doc.doc_id,
                    "text": doc.text,
                    "source_path": doc.source_path,
                    "page": doc.page,
                }
                for doc in documents
            ],
        ),
        project_id=bundle.project_id,
        parent_ids=[bundle.id],
        prep_pipeline_id=pipeline.value,
        documents=documents,
        meta={"prep_metrics": metrics.as_dict()},
    )
    return corpus, metrics


def _extract_file(
    ref: RawFileRef,
    *,
    load_file: FileLoader,
    pipeline: PrepPipelineId,
) -> list[CleanDocument] | None:
    name = ref.original_name
    if is_plaintext_name(name):
        data = load_file(ref.path)
        return extract_plaintext(source_path=name, data=data)

    if is_pdf_name(name):
        if pipeline == PrepPipelineId.PLAINTEXT:
            return None
        data = load_file(ref.path)
        if pipeline == PrepPipelineId.PDF_CLEAN:
            return extract_pdf_clean(source_path=name, data=data)
        if pipeline == PrepPipelineId.DEFAULT:
            return extract_pdf(source_path=name, data=data)
        return None

    return None

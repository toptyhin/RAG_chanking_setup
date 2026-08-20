"""PDF text extraction via pypdf."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath

from pypdf import PdfReader

from rageval_domain import CleanDocument, content_id
from rageval_prep.normalize import clean_pdf_text, normalize_text


def is_pdf_name(name: str) -> bool:
    return PurePosixPath(name).suffix.lower() == ".pdf"


def extract_pdf(
    *,
    source_path: str,
    data: bytes,
    cleaner=normalize_text,
    extractor_tag: str = "pypdf",
) -> list[CleanDocument]:
    reader = PdfReader(BytesIO(data))
    documents: list[CleanDocument] = []
    for page_index, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = cleaner(raw)
        if not text:
            continue
        documents.append(
            CleanDocument(
                doc_id=content_id("doc", source_path, page_index, text),
                text=text,
                source_path=source_path,
                page=page_index,
                meta={"extractor": extractor_tag, "page": page_index},
            )
        )
    return documents


def extract_pdf_clean(*, source_path: str, data: bytes) -> list[CleanDocument]:
    return extract_pdf(
        source_path=source_path,
        data=data,
        cleaner=clean_pdf_text,
        extractor_tag="pypdf_clean",
    )

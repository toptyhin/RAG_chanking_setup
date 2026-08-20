"""Unit tests for prep pipelines."""

from __future__ import annotations

from rageval_domain import RawBundle, RawFileRef
from rageval_prep import PrepPipelineId, extract_plaintext, run_prep
from rageval_prep.pdf import extract_pdf
from tests.helpers.pdf_fixture import pdf_with_text


def test_plaintext_extract() -> None:
    docs = extract_plaintext(source_path="a.txt", data=b"Hello\r\n\r\nworld\n")
    assert len(docs) == 1
    assert docs[0].text == "Hello\n\nworld"
    assert docs[0].doc_id.startswith("doc_")


def test_pdf_extract_nonempty() -> None:
    data = pdf_with_text("Return policy is 14 days")
    docs = extract_pdf(source_path="policy.pdf", data=data)
    assert len(docs) >= 1
    joined = " ".join(d.text for d in docs)
    assert "14" in joined or "Return" in joined or "days" in joined
    assert docs[0].page == 1


def test_run_prep_plaintext_only_skips_pdf() -> None:
    files = {
        "raw_1/files/a.txt": b"alpha text",
        "raw_1/files/b.pdf": pdf_with_text("beta pdf"),
    }
    bundle = RawBundle(
        id="raw_1",
        project_id="proj_1",
        files=[
            RawFileRef(path="raw_1/files/a.txt", original_name="a.txt"),
            RawFileRef(path="raw_1/files/b.pdf", original_name="b.pdf"),
        ],
    )
    corpus, metrics = run_prep(
        bundle, load_file=files.__getitem__, pipeline_id=PrepPipelineId.PLAINTEXT
    )
    assert metrics.files_parsed == 1
    assert metrics.files_skipped == 1
    assert len(corpus.documents) == 1
    assert corpus.documents[0].text == "alpha text"


def test_run_prep_default_includes_pdf() -> None:
    files = {
        "raw_1/files/a.txt": b"alpha text",
        "raw_1/files/b.pdf": pdf_with_text("beta pdf content"),
    }
    bundle = RawBundle(
        id="raw_1",
        project_id="proj_1",
        files=[
            RawFileRef(path="raw_1/files/a.txt", original_name="a.txt"),
            RawFileRef(path="raw_1/files/b.pdf", original_name="b.pdf"),
        ],
    )
    corpus, metrics = run_prep(
        bundle, load_file=files.__getitem__, pipeline_id=PrepPipelineId.DEFAULT
    )
    assert metrics.files_parsed == 2
    assert len(corpus.documents) >= 2

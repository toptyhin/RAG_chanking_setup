from __future__ import annotations

import asyncio
import logging
from collections import Counter
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from rageval_api.deps import ArtifactRepoDep, ObjectStoreDep, ProjectRepoDep
from rageval_api.routes.artifacts import _to_out
from rageval_api.schemas import ArtifactOut
from rageval_api.services.artifact_io import load_artifact_model, persist_artifact_model, update_artifact_model
from rageval_api.services.artifact_naming import naming_meta, source_name_from_record
from rageval_domain import ArtifactType, ChunkSet, CleanCorpus, TestQuery, TestSet
from rageval_domain.query_type import resolve_query_type
from rageval_llm_providers import (
    PROMPT_ID_RAG_QUESTION_PREP,
    TOKEN_ESTIMATE_NOTE,
    LlmConfig,
    LlmConfigStore,
    PromptStore,
    TextLlmProvider,
    allocate_questions_across_parts,
    build_provider,
    estimate_tokens,
    parse_prepared_questions,
    part_question_count,
    plan_document_parts,
    question_prep_schema,
    select_balanced_questions,
)
from rageval_llm_providers.limits import ModelLimits
from rageval_llm_providers.prompts import PromptTemplate
from rageval_llm_providers.question_prep import (
    COMPLETION_RESERVE_TOKENS,
    PreparedQuestion,
    safe_estimate_tokens,
)
from rageval_metadb_sqlite.repositories import ArtifactRecord
from rageval_testgen import (
    EvidenceCandidate,
    chunk_ids_for_spans,
    evidence_candidates,
    resolve_spans_for_quote,
    resolve_spans_for_quotes,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["testsets"])


class TestQueryImport(BaseModel):
    query_id: str | None = None
    text: str = Field(min_length=1)
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    relevant_doc_ids: list[str] = Field(default_factory=list)
    relevant_spans: list[dict] = Field(default_factory=list)
    relevance_grades: dict[str, float] = Field(default_factory=dict)
    expected_answer: str | None = None
    source_quote: str | None = None
    query_type: str | None = None
    source: Literal["synthetic", "manual", "imported"] | None = None
    reviewed: bool | None = None
    label_status: str | None = None
    meta: dict = Field(default_factory=dict)


class TestSetImportRequest(BaseModel):
    queries: list[TestQueryImport] = Field(min_length=1)
    chunk_set_id: str | None = None
    parent_ids: list[str] = Field(default_factory=list)
    validate_chunk_refs: bool = True
    source: Literal["synthetic", "manual", "imported"] = "imported"
    reviewed: bool = False
    meta: dict = Field(default_factory=dict)


class TestQueryPatch(BaseModel):
    """Partial update for one query in a test_set (relevance review)."""

    query_id: str
    relevant_chunk_ids: list[str] | None = None
    relevance_grades: dict[str, float] | None = None
    expected_answer: str | None = None
    source_quote: str | None = None
    query_type: str | None = None
    label_status: str | None = None
    meta: dict | None = None


class TestSetReviewRequest(BaseModel):
    """Verify / correct auto-labeled relevance before a retrieval run."""

    queries: list[TestQueryPatch] = Field(min_length=1)
    mark_verified: bool = True


class TestSetResponse(BaseModel):
    artifact: ArtifactOut
    query_count: int
    source: str
    reviewed: bool
    reviewed_count: int
    source_counts: dict[str, int]


class PrepareQuestionsRequest(BaseModel):
    """Document text comes from clean_corpus (pre-chunking, no overlap)."""

    clean_corpus_id: str
    chunk_set_id: str | None = None
    prompt_id: str = PROMPT_ID_RAG_QUESTION_PREP


class PreparedQuestionOut(BaseModel):
    text: str
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    relevant_spans: list[dict] = Field(default_factory=list)
    evidence_quotes: list[str] = Field(default_factory=list)
    expected_answer: str | None = None
    source_quote: str | None = None
    level: str | None = None
    query_type: str | None = None


class EvidenceCandidatesRequest(BaseModel):
    chunk_set_id: str
    clean_corpus_id: str | None = None
    question: str = Field(min_length=1)
    expected_answer: str | None = None
    source_quote: str | None = None
    evidence_quotes: list[str] = Field(default_factory=list)
    query_type: str | None = None
    limit: int = Field(default=30, ge=1, le=100)


class EvidenceCandidateOut(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    start_char: int | None = None
    end_char: int | None = None
    score: float = 0.0
    reason: str


class EvidenceCandidatesResponse(BaseModel):
    candidates: list[EvidenceCandidateOut]
    quote_spans: list[dict] = Field(default_factory=list)

class PrepareQuestionsResponse(BaseModel):
    questions: list[PreparedQuestionOut]
    provider: TextLlmProvider
    model: str
    prompt_id: str
    prompt_version: int
    clean_corpus_id: str
    document_count: int
    document_chars: int
    corpus_tokens_est: int = 0
    prompt_tokens_est: int = 0
    context_length: int | None = None
    chunk_set_id: str | None = None
    chunk_count: int = 0
    part_count: int = 1


class PrepareEstimateRequest(BaseModel):
    clean_corpus_id: str
    prompt_id: str = PROMPT_ID_RAG_QUESTION_PREP


class PrepareEstimateResponse(BaseModel):
    provider: TextLlmProvider
    model: str
    context_length: int | None
    context_source: str | None = None
    clean_corpus_id: str
    document_count: int
    corpus_chars: int
    corpus_tokens_est: int
    prompt_chars: int
    prompt_tokens_est: int
    fits_context: bool | None = None
    fits_single_pass: bool | None = None
    part_count: int = 1
    token_estimate_note: str = TOKEN_ESTIMATE_NOTE


def _provenance_summary(
    queries: list[TestQuery],
    *,
    fallback_source: str,
) -> tuple[str, bool, int, dict[str, int]]:
    sources = [query.source or fallback_source for query in queries]
    source_counts = dict(Counter(sources))
    source = sources[0] if len(source_counts) == 1 else "mixed"
    reviewed_count = sum(
        1
        for query in queries
        if query.reviewed
        or query.label_status == "verified"
        or query.meta.get("label_status") == "verified"
    )
    return source, bool(queries) and reviewed_count == len(queries), reviewed_count, source_counts


def _llm_store(request: Request) -> LlmConfigStore:
    store = getattr(request.app.state, "llm_config_store", None)
    if store is None:
        settings = request.app.state.settings
        store = LlmConfigStore(Path(settings.data_dir) / "llm_config.json")
        request.app.state.llm_config_store = store
    return store


def _prompt_store(request: Request) -> PromptStore:
    store = getattr(request.app.state, "prompt_store", None)
    if store is None:
        settings = request.app.state.settings
        store = PromptStore(Path(settings.data_dir) / "prompts.json")
        request.app.state.prompt_store = store
    return store


def _configured_model(config: LlmConfig) -> str:
    if config.provider == TextLlmProvider.ollama:
        return config.ollama.model
    if config.provider == TextLlmProvider.openrouter:
        return config.openrouter.model
    return config.gigachat.model


def _document_from_corpus(corpus: CleanCorpus) -> tuple[str, int]:
    parts: list[str] = []
    for doc in corpus.documents:
        text = (doc.text or "").strip()
        if not text:
            continue
        header = doc.doc_id.strip() if doc.doc_id else ""
        parts.append(f"[{header}]\n{text}" if header else text)
    document = "\n\n".join(parts).strip()
    return document, len(parts)


async def _ensure_project(project_id: str, projects: ProjectRepoDep) -> None:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")


async def _load_corpus_artifact(
    project_id: str,
    clean_corpus_id: str,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[ArtifactRecord, CleanCorpus]:
    try:
        clean_record, corpus = await load_artifact_model(
            artifacts,
            store,
            clean_corpus_id,
            CleanCorpus,
            expected_type=ArtifactType.CLEAN_CORPUS.value,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="clean_corpus not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if clean_record.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="clean_corpus belongs to another project",
        )
    return clean_record, corpus


async def _load_project_corpus(
    project_id: str,
    clean_corpus_id: str,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[ArtifactRecord, CleanCorpus]:
    await _ensure_project(project_id, projects)
    return await _load_corpus_artifact(
        project_id, clean_corpus_id, artifacts, store
    )


async def _load_chunk_set_artifact(
    project_id: str,
    chunk_set_id: str,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[ArtifactRecord, ChunkSet]:
    try:
        chunk_record, chunk_set = await load_artifact_model(
            artifacts,
            store,
            chunk_set_id,
            ChunkSet,
            expected_type=ArtifactType.CHUNK_SET.value,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="chunk_set not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if chunk_record.project_id != project_id:
        raise HTTPException(status_code=400, detail="chunk_set belongs to another project")
    return chunk_record, chunk_set


async def _load_project_chunk_set(
    project_id: str,
    chunk_set_id: str,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[ArtifactRecord, ChunkSet]:
    await _ensure_project(project_id, projects)
    return await _load_chunk_set_artifact(
        project_id, chunk_set_id, artifacts, store
    )


async def _load_project_test_set(
    project_id: str,
    test_set_id: str,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[ArtifactRecord, TestSet]:
    await _ensure_project(project_id, projects)
    try:
        record, test_set = await load_artifact_model(
            artifacts,
            store,
            test_set_id,
            TestSet,
            expected_type=ArtifactType.TEST_SET.value,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="test_set not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if record.project_id != project_id:
        raise HTTPException(status_code=400, detail="test_set belongs to another project")
    return record, test_set


async def _fetch_model_limits(provider: object) -> ModelLimits | None:
    try:
        return await asyncio.to_thread(provider.get_model_limits)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None


def _estimate_context_fit(
    *,
    rendered: str,
    skeleton: str,
    document: str,
    context_length: int | None,
) -> tuple[bool | None, bool | None, int]:
    fits: bool | None = None
    fits_single: bool | None = None
    part_count = 1
    if context_length and context_length > 0:
        fits_single = (
            safe_estimate_tokens(rendered) + COMPLETION_RESERVE_TOKENS
            <= context_length
        )
        try:
            parts = plan_document_parts(
                document,
                overhead_tokens=estimate_tokens(skeleton),
                context_length=context_length,
            )
            part_count = max(1, len(parts))
            fits = part_count >= 1
        except ValueError:
            fits = False
            part_count = 0
    return fits, fits_single, part_count


def _chunk_pairs_from_set(chunk_set: ChunkSet) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for chunk in chunk_set.chunks:
        text = (chunk.text or "").strip()
        if text:
            pairs.append((chunk.chunk_id, text))
    return pairs


async def _load_optional_chunk_pairs(
    project_id: str,
    chunk_set_id: str | None,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[str | None, ChunkSet | None, list[tuple[str, str]]]:
    if not chunk_set_id:
        return None, None, []
    _, loaded_chunk_set = await _load_chunk_set_artifact(
        project_id, chunk_set_id, artifacts, store
    )
    return chunk_set_id, loaded_chunk_set, _chunk_pairs_from_set(loaded_chunk_set)


def _validate_question_prep_prompt(
    prompt_store: PromptStore,
    prompt_id: str,
) -> PromptTemplate:
    try:
        prompt = prompt_store.get(prompt_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"prompt not found: {prompt_id}",
        ) from exc
    try:
        _ = prompt_store.active_response_schema(prompt_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return prompt


def _plan_prep_document_parts(
    document: str,
    skeleton: str,
    context_length: int | None,
) -> list[str]:
    try:
        document_parts = plan_document_parts(
            document,
            overhead_tokens=estimate_tokens(skeleton),
            context_length=context_length,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not document_parts:
        raise HTTPException(status_code=400, detail="clean_corpus documents are empty")
    return document_parts


def _dump_raw_llm_response(request: Request, raw_parts: list[str]) -> None:
    try:
        settings = request.app.state.settings
        log_dir = Path(settings.data_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        dump_path = log_dir / "last_prepare_questions_raw.txt"
        dump_path.write_text(
            "\n\n===== PART BREAK =====\n\n".join(raw_parts),
            encoding="utf-8",
        )
        logger.error("raw LLM response also saved to %s", dump_path)
    except Exception:  # noqa: BLE001
        logger.exception("failed to write raw LLM response dump")


def _raise_parse_failure(
    exc: ValueError,
    *,
    raw: str,
    raw_parts: list[str],
    request: Request,
    llm_config: LlmConfig,
    model: str,
    part_index: int,
    part_count: int,
) -> None:
    logger.error(
        "could not parse LLM questions (%s/%s) part=%s/%s: %s\n"
        "--- raw LLM response (%d chars) ---\n%s\n--- end raw LLM response ---",
        llm_config.provider,
        model,
        part_index + 1,
        part_count,
        exc,
        len(raw),
        raw,
    )
    _dump_raw_llm_response(request, raw_parts)
    preview = raw if len(raw) <= 800 else f"{raw[:400]}\n…\n{raw[-400:]}"
    raise HTTPException(
        status_code=502,
        detail=(
            f"could not parse LLM questions: {exc}\n"
            f"(provider={llm_config.provider}/{model}, "
            f"part={part_index + 1}/{part_count}, chars={len(raw)})\n"
            f"raw preview:\n{preview}"
        ),
    ) from exc


async def _generate_parsed_questions_from_parts(
    *,
    request: Request,
    prompt_store: PromptStore,
    prompt_id: str,
    document_parts: list[str],
    chunk_pairs: list[tuple[str, str]],
    provider: object,
    llm_config: LlmConfig,
    model: str,
    context_length: int | None,
) -> tuple[list[PreparedQuestion], int]:
    allocations = allocate_questions_across_parts(len(document_parts))
    raw_parts: list[str] = []
    parsed_all: list[PreparedQuestion] = []
    prompt_tokens_total = 0

    for part_index, (part_text, level_counts) in enumerate(
        zip(document_parts, allocations, strict=True)
    ):
        count = part_question_count(level_counts)
        if count < 1:
            continue
        part_schema = question_prep_schema(count=count)
        part_prompt = prompt_store.render_active(
            prompt_id,
            document=part_text,
            question_count=count,
            level_counts=level_counts,
            response_schema=part_schema,
        )
        prompt_tokens_total += estimate_tokens(part_prompt)
        if (
            context_length
            and context_length > 0
            and safe_estimate_tokens(part_prompt) + COMPLETION_RESERVE_TOKENS
            > context_length
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Document part {part_index + 1}/{len(document_parts)} still "
                    f"exceeds model context ({context_length} tokens for {model}). "
                    "Use a model with a larger context window."
                ),
            )
        try:
            raw = await asyncio.to_thread(
                provider.generate,  # type: ignore[attr-defined]
                part_prompt,
                response_format=part_schema,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "LLM generate failed (%s/%s) part=%s/%s: %s",
                llm_config.provider,
                model,
                part_index + 1,
                len(document_parts),
                exc,
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    f"LLM generate failed ({llm_config.provider}/{model}) "
                    f"part {part_index + 1}/{len(document_parts)}: {exc}"
                ),
            ) from exc
        raw_parts.append(raw)
        try:
            parsed_all.extend(parse_prepared_questions(raw, chunk_pairs or None))
        except ValueError as exc:
            _raise_parse_failure(
                exc,
                raw=raw,
                raw_parts=raw_parts,
                request=request,
                llm_config=llm_config,
                model=model,
                part_index=part_index,
                part_count=len(document_parts),
            )

    return parsed_all, prompt_tokens_total


def _build_prepared_question_out(
    q: PreparedQuestion,
    corpus: CleanCorpus,
    loaded_chunk_set: ChunkSet | None,
) -> PreparedQuestionOut:
    quotes = list(q.evidence_quotes)
    if not quotes and q.source_quote:
        quotes = [q.source_quote]
    quote_spans = resolve_spans_for_quotes(corpus, quotes) if quotes else []
    span_chunk_ids = (
        chunk_ids_for_spans(loaded_chunk_set, quote_spans)
        if loaded_chunk_set is not None
        else []
    )
    relevant = span_chunk_ids or list(q.relevant_chunk_ids)
    return PreparedQuestionOut(
        text=q.text,
        relevant_chunk_ids=relevant,
        relevant_spans=quote_spans,
        evidence_quotes=quotes,
        expected_answer=q.expected_answer,
        source_quote=q.source_quote,
        level=q.level,
        query_type=q.query_type,
    )


async def _resolve_evidence_clean_corpus_id(
    chunk_set: ChunkSet,
    chunk_record: ArtifactRecord,
    clean_corpus_id: str | None,
    artifacts: ArtifactRepoDep,
) -> str | None:
    if clean_corpus_id:
        return clean_corpus_id
    for parent_id in chunk_set.parent_ids or chunk_record.parent_ids:
        parent = await artifacts.get(parent_id)
        if parent and parent.type == ArtifactType.CLEAN_CORPUS.value:
            return parent_id
    return None


def _resolve_evidence_quote_spans(
    corpus: CleanCorpus,
    body: EvidenceCandidatesRequest,
) -> list[dict]:
    quotes = list(body.evidence_quotes)
    if not quotes and body.source_quote:
        quotes = [body.source_quote]
    if quotes:
        return resolve_spans_for_quotes(corpus, quotes)
    if body.source_quote:
        return resolve_spans_for_quote(corpus, body.source_quote)
    return []


def _promote_quote_span_candidates(
    chunk_set: ChunkSet,
    candidates: list[EvidenceCandidate],
    quote_spans: list[dict],
    limit: int,
) -> list[EvidenceCandidateOut]:
    by_id = {c.chunk_id: c for c in candidates}
    promoted: list[EvidenceCandidateOut] = []
    seen: set[str] = set()
    for cid in chunk_ids_for_spans(chunk_set, quote_spans):
        chunk = next((c for c in chunk_set.chunks if c.chunk_id == cid), None)
        if chunk is None:
            continue
        existing = by_id.get(cid)
        promoted.append(
            EvidenceCandidateOut(
                chunk_id=cid,
                doc_id=chunk.doc_id,
                text=chunk.text or "",
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                score=float(existing.score) if existing else 1.0,
                reason="quote",
            )
        )
        seen.add(cid)
    for c in candidates:
        if c.chunk_id in seen:
            continue
        promoted.append(EvidenceCandidateOut(**c.as_dict()))
        seen.add(c.chunk_id)
        if len(promoted) >= limit:
            break
    return promoted[:limit]


async def _load_import_chunk_context(
    project_id: str,
    body: TestSetImportRequest,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> tuple[set[str] | None, list[str], str | None, ChunkSet | None]:
    known_chunks: set[str] | None = None
    parent_ids = list(body.parent_ids)
    source: str | None = None
    loaded_chunk_set: ChunkSet | None = None
    if not body.chunk_set_id:
        return known_chunks, parent_ids, source, loaded_chunk_set

    chunk_record, loaded_chunk_set = await _load_chunk_set_artifact(
        project_id, body.chunk_set_id, artifacts, store
    )
    known_chunks = {c.chunk_id for c in loaded_chunk_set.chunks}
    if body.chunk_set_id not in parent_ids:
        parent_ids.append(body.chunk_set_id)
    source = source_name_from_record(chunk_record)
    return known_chunks, parent_ids, source, loaded_chunk_set


def _import_label_status(
    item: TestQueryImport,
    spans: list,
    chunk_ids: list[str],
) -> str | None:
    if item.label_status is not None:
        return item.label_status
    if spans:
        return "verified"
    if chunk_ids:
        return "auto"
    return None


def _build_import_query(
    item: TestQueryImport,
    body: TestSetImportRequest,
    *,
    spans: list,
    chunk_ids: list[str],
    label_status: str | None,
) -> TestQuery:
    query_source = item.source or body.source
    reviewed = (
        item.reviewed
        if item.reviewed is not None
        else body.reviewed or label_status == "verified"
    )
    q = TestQuery(
        text=item.text,
        relevant_chunk_ids=chunk_ids,
        relevant_doc_ids=item.relevant_doc_ids,
        relevant_spans=spans,
        relevance_grades=item.relevance_grades,
        expected_answer=item.expected_answer,
        source_quote=item.source_quote,
        query_type=resolve_query_type(
            query_type=item.query_type,
            meta=item.meta if isinstance(item.meta, dict) else None,
        ),
        source=query_source,
        reviewed=reviewed,
        label_status=label_status,
        meta={
            **item.meta,
            "source": query_source,
            "reviewed": reviewed,
        },
    )
    if item.query_id:
        q.query_id = item.query_id
    return q


def _build_import_queries(
    body: TestSetImportRequest,
    *,
    known_chunks: set[str] | None,
    loaded_chunk_set: ChunkSet | None,
) -> list[TestQuery]:
    queries: list[TestQuery] = []
    for item in body.queries:
        spans = list(item.relevant_spans)
        chunk_ids = list(item.relevant_chunk_ids)
        if spans and loaded_chunk_set is not None and not chunk_ids:
            chunk_ids = chunk_ids_for_spans(loaded_chunk_set, spans)
        if body.validate_chunk_refs and known_chunks is not None:
            missing = [cid for cid in chunk_ids if cid not in known_chunks]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"unknown relevant_chunk_ids: {missing}",
                )
        label_status = _import_label_status(item, spans, chunk_ids)
        queries.append(
            _build_import_query(
                item,
                body,
                spans=spans,
                chunk_ids=chunk_ids,
                label_status=label_status,
            )
        )
    return queries


def _apply_review_patch(
    query: TestQuery,
    patch: TestQueryPatch,
    *,
    mark_verified: bool,
) -> None:
    if patch.relevant_chunk_ids is not None:
        query.relevant_chunk_ids = patch.relevant_chunk_ids
    if patch.relevance_grades is not None:
        query.relevance_grades = patch.relevance_grades
    if patch.expected_answer is not None:
        query.expected_answer = patch.expected_answer
    if patch.source_quote is not None:
        query.source_quote = patch.source_quote
    if patch.query_type is not None:
        query.query_type = patch.query_type
    if patch.meta is not None:
        query.meta = {**query.meta, **patch.meta}
    if patch.label_status is not None:
        query.label_status = patch.label_status
    elif mark_verified:
        query.label_status = "verified"
    query.reviewed = query.label_status == "verified"
    query.meta = {
        **query.meta,
        "label_status": query.label_status,
        "reviewed": query.reviewed,
    }


@router.post(
    "/projects/{project_id}/test-sets/prepare-estimate",
    response_model=PrepareEstimateResponse,
)
async def prepare_questions_estimate(
    project_id: str,
    body: PrepareEstimateRequest,
    request: Request,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> PrepareEstimateResponse:
    """Estimate corpus/prompt tokens vs selected model context length."""
    _, corpus = await _load_project_corpus(
        project_id, body.clean_corpus_id, projects, artifacts, store
    )
    document, document_count = _document_from_corpus(corpus)
    prompt_store = _prompt_store(request)
    try:
        rendered = prompt_store.render_active(body.prompt_id, document=document)
        skeleton = prompt_store.render_active(body.prompt_id, document="")
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"prompt not found: {body.prompt_id}",
        ) from exc

    llm_config = _llm_store(request).load()
    model = _configured_model(llm_config)
    provider = build_provider(llm_config)
    limits = await _fetch_model_limits(provider)
    context_length = limits.context_length if limits else None
    fits, fits_single, part_count = _estimate_context_fit(
        rendered=rendered,
        skeleton=skeleton,
        document=document,
        context_length=context_length,
    )

    return PrepareEstimateResponse(
        provider=llm_config.provider,
        model=model,
        context_length=context_length,
        context_source=limits.source if limits else None,
        clean_corpus_id=body.clean_corpus_id,
        document_count=document_count,
        corpus_chars=len(document),
        corpus_tokens_est=estimate_tokens(document),
        prompt_chars=len(rendered),
        prompt_tokens_est=estimate_tokens(rendered),
        fits_context=fits,
        fits_single_pass=fits_single,
        part_count=part_count,
        token_estimate_note=TOKEN_ESTIMATE_NOTE,
    )


@router.post(
    "/projects/{project_id}/test-sets/prepare",
    response_model=PrepareQuestionsResponse,
)
async def prepare_questions(
    project_id: str,
    body: PrepareQuestionsRequest,
    request: Request,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> PrepareQuestionsResponse:
    """Generate golden questions from clean corpus text via configured LLM."""
    _, corpus = await _load_project_corpus(
        project_id, body.clean_corpus_id, projects, artifacts, store
    )
    document, document_count = _document_from_corpus(corpus)
    if not document:
        raise HTTPException(status_code=400, detail="clean_corpus documents are empty")

    chunk_set_id, loaded_chunk_set, chunk_pairs = await _load_optional_chunk_pairs(
        project_id, body.chunk_set_id, artifacts, store
    )

    prompt_store = _prompt_store(request)
    prompt = _validate_question_prep_prompt(prompt_store, body.prompt_id)
    rendered = prompt_store.render_active(body.prompt_id, document=document)
    skeleton = prompt_store.render_active(body.prompt_id, document="")

    llm_config = _llm_store(request).load()
    model = _configured_model(llm_config)
    provider = build_provider(llm_config)
    limits = await _fetch_model_limits(provider)
    context_length = limits.context_length if limits else None
    document_parts = _plan_prep_document_parts(document, skeleton, context_length)

    parsed_all, prompt_tokens_total = await _generate_parsed_questions_from_parts(
        request=request,
        prompt_store=prompt_store,
        prompt_id=body.prompt_id,
        document_parts=document_parts,
        chunk_pairs=chunk_pairs,
        provider=provider,
        llm_config=llm_config,
        model=model,
        context_length=context_length,
    )

    parsed = select_balanced_questions(parsed_all)
    if not parsed:
        raise HTTPException(
            status_code=502,
            detail="LLM returned no usable questions after merging parts",
        )

    questions_out = [
        _build_prepared_question_out(q, corpus, loaded_chunk_set) for q in parsed
    ]

    return PrepareQuestionsResponse(
        questions=questions_out,
        provider=llm_config.provider,
        model=model,
        prompt_id=prompt.id,
        prompt_version=prompt.active_version,
        clean_corpus_id=body.clean_corpus_id,
        document_count=document_count,
        document_chars=len(document),
        corpus_tokens_est=estimate_tokens(document),
        prompt_tokens_est=prompt_tokens_total or estimate_tokens(rendered),
        context_length=limits.context_length if limits else None,
        chunk_set_id=chunk_set_id,
        chunk_count=len(chunk_pairs),
        part_count=len(document_parts),
    )


@router.post(
    "/projects/{project_id}/test-sets/evidence-candidates",
    response_model=EvidenceCandidatesResponse,
)
async def get_evidence_candidates(
    project_id: str,
    body: EvidenceCandidatesRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> EvidenceCandidatesResponse:
    """Suggest evidence chunks for gold labeling (quote + BM25 + neighbors)."""
    chunk_record, chunk_set = await _load_project_chunk_set(
        project_id, body.chunk_set_id, projects, artifacts, store
    )
    if not chunk_set.chunks:
        raise HTTPException(status_code=400, detail="chunk_set has 0 chunks")

    quote_spans: list[dict] = []
    clean_id = await _resolve_evidence_clean_corpus_id(
        chunk_set, chunk_record, body.clean_corpus_id, artifacts
    )
    if clean_id:
        _, corpus = await _load_corpus_artifact(
            project_id, clean_id, artifacts, store
        )
        quote_spans = _resolve_evidence_quote_spans(corpus, body)

    candidates = evidence_candidates(
        chunk_set,
        question=body.question,
        expected_answer=body.expected_answer,
        source_quote=body.source_quote,
        query_type=body.query_type,
        limit=body.limit,
    )
    if quote_spans:
        promoted = _promote_quote_span_candidates(
            chunk_set, candidates, quote_spans, body.limit
        )
        return EvidenceCandidatesResponse(
            candidates=promoted,
            quote_spans=quote_spans,
        )

    return EvidenceCandidatesResponse(
        candidates=[EvidenceCandidateOut(**c.as_dict()) for c in candidates],
        quote_spans=quote_spans,
    )


@router.post(
    "/projects/{project_id}/test-sets/import",
    response_model=TestSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_test_set(
    project_id: str,
    body: TestSetImportRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> TestSetResponse:
    await _ensure_project(project_id, projects)
    known_chunks, parent_ids, source, loaded_chunk_set = await _load_import_chunk_context(
        project_id, body, artifacts, store
    )
    queries = _build_import_queries(
        body,
        known_chunks=known_chunks,
        loaded_chunk_set=loaded_chunk_set,
    )

    test_source, test_reviewed, reviewed_count, source_counts = _provenance_summary(
        queries,
        fallback_source=body.source,
    )
    test_set = TestSet(
        project_id=project_id,
        parent_ids=parent_ids,
        queries=queries,
        source=test_source,
        reviewed=test_reviewed,
        meta={
            **body.meta,
            "source": test_source,
            "reviewed": test_reviewed,
            "reviewed_count": reviewed_count,
            "source_counts": source_counts,
        },
    )
    record = await persist_artifact_model(
        artifacts,
        store,
        model=test_set,
        artifact_id=test_set.id,
        project_id=project_id,
        artifact_type=ArtifactType.TEST_SET.value,
        parent_ids=parent_ids,
        meta={
            "query_count": len(queries),
            "chunk_set_id": body.chunk_set_id,
            "source": test_source,
            "reviewed": test_reviewed,
            "reviewed_count": reviewed_count,
            "source_counts": source_counts,
            **naming_meta(ArtifactType.TEST_SET.value, source),
        },
    )
    return TestSetResponse(
        artifact=await _to_out(record, store, artifacts),
        query_count=len(queries),
        source=test_source,
        reviewed=test_reviewed,
        reviewed_count=reviewed_count,
        source_counts=source_counts,
    )


@router.patch(
    "/projects/{project_id}/test-sets/{test_set_id}/review",
    response_model=TestSetResponse,
)
async def review_test_set(
    project_id: str,
    test_set_id: str,
    body: TestSetReviewRequest,
    projects: ProjectRepoDep,
    artifacts: ArtifactRepoDep,
    store: ObjectStoreDep,
) -> TestSetResponse:
    """Confirm or correct auto-labeled relevance (stage 59)."""
    _, test_set = await _load_project_test_set(
        project_id, test_set_id, projects, artifacts, store
    )

    by_id = {q.query_id: q for q in test_set.queries}
    for patch in body.queries:
        query = by_id.get(patch.query_id)
        if query is None:
            raise HTTPException(
                status_code=400, detail=f"unknown query_id: {patch.query_id}"
            )
        _apply_review_patch(query, patch, mark_verified=body.mark_verified)

    source, reviewed, reviewed_count, source_counts = _provenance_summary(
        test_set.queries,
        fallback_source=test_set.source,
    )
    test_set.source = source
    test_set.reviewed = reviewed
    test_set.meta = {
        **test_set.meta,
        "label_status": "verified" if reviewed else "partial",
        "source": source,
        "reviewed": reviewed,
        "reviewed_count": reviewed_count,
        "source_counts": source_counts,
    }

    updated = await update_artifact_model(
        artifacts,
        store,
        model=test_set,
        artifact_id=test_set.id,
        meta={
            "query_count": len(test_set.queries),
            "label_status": test_set.meta.get("label_status"),
            "source": source,
            "reviewed": reviewed,
            "reviewed_count": reviewed_count,
            "source_counts": source_counts,
        },
    )
    return TestSetResponse(
        artifact=await _to_out(updated, store, artifacts),
        query_count=len(test_set.queries),
        source=source,
        reviewed=reviewed,
        reviewed_count=reviewed_count,
        source_counts=source_counts,
    )

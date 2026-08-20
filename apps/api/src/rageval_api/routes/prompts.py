"""Versioned prompt templates (RAG question prep, etc.)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rageval_llm_providers import (
    DOCUMENT_PLACEHOLDER,
    SCHEMA_PLACEHOLDER,
    PromptStore,
    PromptTemplate,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptVersionOut(BaseModel):
    version: int
    body: str
    created_at: str
    note: str | None = None


class PromptOut(BaseModel):
    id: str
    name: str
    description: str
    active_version: int
    active_body: str
    document_placeholder: str = DOCUMENT_PLACEHOLDER
    schema_placeholder: str = SCHEMA_PLACEHOLDER
    response_schema: dict[str, Any]
    versions: list[PromptVersionOut]


class PromptListOut(BaseModel):
    prompts: list[PromptOut]


class SavePromptVersionIn(BaseModel):
    body: str = Field(min_length=1)
    note: str | None = None
    activate: bool = True
    response_schema: dict[str, Any] | None = None


class SetActiveVersionIn(BaseModel):
    version: int = Field(ge=1)


class SetResponseSchemaIn(BaseModel):
    response_schema: dict[str, Any]


def _store(request: Request) -> PromptStore:
    store = getattr(request.app.state, "prompt_store", None)
    if store is None:
        settings = request.app.state.settings
        path = Path(settings.data_dir) / "prompts.json"
        store = PromptStore(path)
        request.app.state.prompt_store = store
    return store


def _to_out(prompt: PromptTemplate) -> PromptOut:
    return PromptOut(
        id=prompt.id,
        name=prompt.name,
        description=prompt.description,
        active_version=prompt.active_version,
        active_body=prompt.active_body(),
        document_placeholder=DOCUMENT_PLACEHOLDER,
        schema_placeholder=SCHEMA_PLACEHOLDER,
        response_schema=prompt.response_schema,
        versions=[
            PromptVersionOut(
                version=v.version,
                body=v.body,
                created_at=v.created_at,
                note=v.note,
            )
            for v in sorted(prompt.versions, key=lambda x: x.version, reverse=True)
        ],
    )


@router.get("", response_model=PromptListOut)
def list_prompts(request: Request) -> PromptListOut:
    catalog = _store(request).load()
    return PromptListOut(prompts=[_to_out(p) for p in catalog.prompts])


@router.get("/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: str, request: Request) -> PromptOut:
    try:
        return _to_out(_store(request).get(prompt_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"prompt not found: {prompt_id}") from exc


@router.post("/{prompt_id}/versions", response_model=PromptOut)
def save_prompt_version(
    prompt_id: str,
    body: SavePromptVersionIn,
    request: Request,
) -> PromptOut:
    try:
        updated = _store(request).save_new_version(
            prompt_id,
            body.body,
            note=body.note,
            activate=body.activate,
            response_schema=body.response_schema,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"prompt not found: {prompt_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(updated)


@router.put("/{prompt_id}/schema", response_model=PromptOut)
def set_response_schema(
    prompt_id: str,
    body: SetResponseSchemaIn,
    request: Request,
) -> PromptOut:
    try:
        updated = _store(request).set_response_schema(
            prompt_id,
            body.response_schema,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"prompt not found: {prompt_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(updated)


@router.put("/{prompt_id}/active", response_model=PromptOut)
def set_active_version(
    prompt_id: str,
    body: SetActiveVersionIn,
    request: Request,
) -> PromptOut:
    try:
        updated = _store(request).set_active_version(prompt_id, body.version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"prompt not found: {prompt_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(updated)


@router.post("/{prompt_id}/reset", response_model=PromptOut)
def reset_prompt(prompt_id: str, request: Request) -> PromptOut:
    try:
        updated = _store(request).reset_to_default(prompt_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"prompt not found: {prompt_id}") from exc
    return _to_out(updated)

"""Versioned prompt templates for LLM-assisted workflows (JSON under DATA_DIR)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from rageval_llm_providers.question_prep import (
    QUESTION_PREP_TOTAL,
    default_level_counts,
    format_level_counts,
    question_prep_schema,
)

PROMPT_ID_RAG_QUESTION_PREP = "rag_question_prep"

DOCUMENT_PLACEHOLDER = "{{document}}"
SCHEMA_PLACEHOLDER = "{{response_schema}}"
QUESTION_COUNT_PLACEHOLDER = "{{question_count}}"
LEVEL_COUNTS_PLACEHOLDER = "{{level_counts}}"

DEFAULT_RAG_QUESTION_PREP_BODY = f"""Ты готовишь эталонный набор вопросов для оценки RAG-системы.

Тебе дан текст документа (полный документ или один фрагмент). Используй ТОЛЬКО факты из этого текста — не опирайся на внешние знания.

Задача:
1. Составь ровно {QUESTION_COUNT_PLACEHOLDER} вопросов по документу — массив "questions" длины {QUESTION_COUNT_PLACEHOLDER}.
2. Распредели вопросы строго по уровням сложности. В поле "level" пиши ТОЛЬКО одно из enum: "L1", "L2", "L3", "L4".
   Квота по уровням для ЭТОГО ответа (сумма = {QUESTION_COUNT_PLACEHOLDER}):
{LEVEL_COUNTS_PLACEHOLDER}

Определения уровней (обязательны):
- L1 (факт): ответ явно и дословно (или почти дословно) содержится в одном непрерывном фрагменте; вопрос можно закрыть одним span без рассуждений.
- L2 (перефраз): ответ в одном фрагменте, но вопрос сформулирован иначе (синонимы, перестановка, обобщение формулировки); нужен парафраз, не дословный keyword-match.
- L3 (связь / multi-hop): чтобы ответить, нужно сопоставить информацию из 2+ разных фрагментов документа; один фрагмент недостаточен.
- L4 (вывод): ответ следует из текста логически, но не процитирован дословно; делай только осторожный вывод строго по тексту, без внешних знаний и домыслов.

3. Каждый элемент "questions" обязан содержать ВСЕ поля схемы (имена полей — дословно):
   - "level" — одно из: "L1", "L2", "L3", "L4"
   - "question" — текст вопроса
   - "expected_answer" — правильный ответ (формулировка или сжатая цитата из текста)
   - "source_quote" — опорная цитата из документа (для L1/L2 — фрагмент с ответом)
   - "evidence_quotes" — массив строк, дословные цитаты-посылки из документа:
       * L1/L2: минимум 1 элемент (тот же или близкий к source_quote)
       * L3: минимум 2 разных фрагмента, без которых нельзя ответить
       * L4: 1–N фактов-посылок, из которых следует вывод (не готовый ответ)
4. Не задавай вопросы, на которые нельзя ответить по тексту. Не дублируй почти одинаковые вопросы.
5. В строках JSON не ломай кавычки: если в цитате есть ", экранируй как \\".

Документ:
{DOCUMENT_PLACEHOLDER}

Верни ТОЛЬКО один JSON-объект без пояснений и без markdown-ограждений.
Ответ ОБЯЗАН соответствовать JSON Schema ниже (корневой объект с полем "questions"):
{SCHEMA_PLACEHOLDER}
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_question_prep_schema() -> dict[str, Any]:
    return question_prep_schema(count=QUESTION_PREP_TOTAL)


def validate_response_schema(schema: Any) -> dict[str, Any]:
    """Require a JSON Schema object suitable for Ollama ``format``."""
    if not isinstance(schema, dict) or not schema:
        raise ValueError("response_schema must be a non-empty JSON object")
    schema_type = schema.get("type")
    if schema_type is not None and schema_type != "object":
        raise ValueError('response_schema.type must be "object" (Ollama format)')
    if "properties" not in schema and "$ref" not in schema:
        raise ValueError("response_schema must declare properties (or $ref)")
    return schema


class PromptVersion(BaseModel):
    version: int
    body: str
    created_at: str
    note: str | None = None


class PromptTemplate(BaseModel):
    id: str
    name: str
    description: str = ""
    active_version: int
    versions: list[PromptVersion] = Field(default_factory=list)
    # Active JSON Schema for constrained decoding (Ollama ``format``).
    response_schema: dict[str, Any] = Field(
        default_factory=default_question_prep_schema
    )

    def version(self, number: int) -> PromptVersion | None:
        for item in self.versions:
            if item.version == number:
                return item
        return None

    def active_body(self) -> str:
        found = self.version(self.active_version)
        if found is not None:
            return found.body
        if self.versions:
            return self.versions[-1].body
        return ""


class PromptCatalog(BaseModel):
    prompts: list[PromptTemplate] = Field(default_factory=list)

    def get(self, prompt_id: str) -> PromptTemplate | None:
        for item in self.prompts:
            if item.id == prompt_id:
                return item
        return None


def default_rag_question_prep() -> PromptTemplate:
    return PromptTemplate(
        id=PROMPT_ID_RAG_QUESTION_PREP,
        name="RAG question prep",
        description=(
            "Generate labeled RAG evaluation questions from full document "
            "context (difficulty levels + expected answers)."
        ),
        active_version=1,
        versions=[
            PromptVersion(
                version=1,
                body=DEFAULT_RAG_QUESTION_PREP_BODY.strip() + "\n",
                created_at=_utc_now_iso(),
                note="default v4: prompt embeds {{response_schema}}",
            )
        ],
        response_schema=default_question_prep_schema(),
    )


def default_catalog() -> PromptCatalog:
    return PromptCatalog(prompts=[default_rag_question_prep()])


class PromptStore:
    """Load / save versioned prompts from ``data_dir/prompts.json``."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> PromptCatalog:
        if not self.path.is_file():
            catalog = default_catalog()
            self.save(catalog)
            return catalog
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            catalog = default_catalog()
            self.save(catalog)
            return catalog
        catalog = PromptCatalog.model_validate(raw)
        dirty = False
        if catalog.get(PROMPT_ID_RAG_QUESTION_PREP) is None:
            catalog.prompts.append(default_rag_question_prep())
            dirty = True
        prep = catalog.get(PROMPT_ID_RAG_QUESTION_PREP)
        if prep is not None:
            if not prep.response_schema:
                prep.response_schema = default_question_prep_schema()
                dirty = True
            active = prep.active_body()
            questions_prop = (
                (prep.response_schema or {}).get("properties", {}).get("questions")
                if isinstance(prep.response_schema, dict)
                else None
            )
            old_count = (
                questions_prop.get("minItems")
                if isinstance(questions_prop, dict)
                else None
            )
            needs_schema_placeholder = SCHEMA_PLACEHOLDER not in active
            needs_twelve_default = (
                "ровно 10" in active
                or old_count == 10
                or (
                    DOCUMENT_PLACEHOLDER in active
                    and SCHEMA_PLACEHOLDER in active
                    and QUESTION_COUNT_PLACEHOLDER not in active
                    and "минимум 2 вопроса" in active
                )
            )
            if needs_schema_placeholder or needs_twelve_default:
                next_version = max((v.version for v in prep.versions), default=0) + 1
                note = (
                    f"auto: {QUESTION_PREP_TOTAL} questions (3 per L1–L4)"
                    if needs_twelve_default
                    else "auto: embed {{response_schema}} + align fields"
                )
                prep.versions.append(
                    PromptVersion(
                        version=next_version,
                        body=DEFAULT_RAG_QUESTION_PREP_BODY.strip() + "\n",
                        created_at=_utc_now_iso(),
                        note=note,
                    )
                )
                prep.active_version = next_version
                prep.response_schema = default_question_prep_schema()
                dirty = True
        if dirty:
            self.save(catalog)
        return catalog

    def save(self, catalog: PromptCatalog) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = catalog.model_dump(mode="json")
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def get(self, prompt_id: str) -> PromptTemplate:
        catalog = self.load()
        found = catalog.get(prompt_id)
        if found is None:
            raise KeyError(prompt_id)
        return found

    def save_new_version(
        self,
        prompt_id: str,
        body: str,
        *,
        note: str | None = None,
        activate: bool = True,
        response_schema: dict[str, Any] | None = None,
    ) -> PromptTemplate:
        catalog = self.load()
        prompt = catalog.get(prompt_id)
        if prompt is None:
            raise KeyError(prompt_id)
        next_version = max((v.version for v in prompt.versions), default=0) + 1
        prompt.versions.append(
            PromptVersion(
                version=next_version,
                body=body,
                created_at=_utc_now_iso(),
                note=note,
            )
        )
        if activate:
            prompt.active_version = next_version
        if response_schema is not None:
            prompt.response_schema = validate_response_schema(response_schema)
        self.save(catalog)
        return prompt

    def set_response_schema(
        self,
        prompt_id: str,
        schema: dict[str, Any],
    ) -> PromptTemplate:
        catalog = self.load()
        prompt = catalog.get(prompt_id)
        if prompt is None:
            raise KeyError(prompt_id)
        prompt.response_schema = validate_response_schema(schema)
        self.save(catalog)
        return prompt

    def set_active_version(self, prompt_id: str, version: int) -> PromptTemplate:
        catalog = self.load()
        prompt = catalog.get(prompt_id)
        if prompt is None:
            raise KeyError(prompt_id)
        if prompt.version(version) is None:
            raise ValueError(f"version {version} not found for prompt {prompt_id}")
        prompt.active_version = version
        self.save(catalog)
        return prompt

    def reset_to_default(self, prompt_id: str) -> PromptTemplate:
        if prompt_id != PROMPT_ID_RAG_QUESTION_PREP:
            raise KeyError(prompt_id)
        return self.save_new_version(
            prompt_id,
            DEFAULT_RAG_QUESTION_PREP_BODY.strip() + "\n",
            note="reset to default",
            activate=True,
            response_schema=default_question_prep_schema(),
        )

    def render_active(
        self,
        prompt_id: str,
        *,
        document: str,
        question_count: int | None = None,
        level_counts: dict[str, int] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        """Substitute document / schema / question-count placeholders."""
        prompt = self.get(prompt_id)
        counts = level_counts or default_level_counts()
        count = (
            question_count
            if question_count is not None
            else sum(int(v) for v in counts.values())
        )
        schema = response_schema or prompt.response_schema or default_question_prep_schema()
        schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
        level_text = format_level_counts(counts)
        body = prompt.active_body()
        rendered = (
            body.replace(DOCUMENT_PLACEHOLDER, document)
            .replace(SCHEMA_PLACEHOLDER, schema_text)
            .replace(QUESTION_COUNT_PLACEHOLDER, str(count))
            .replace(LEVEL_COUNTS_PLACEHOLDER, level_text)
        )
        # Older custom prompts without count placeholders: append a quota note.
        if (
            QUESTION_COUNT_PLACEHOLDER not in body
            or LEVEL_COUNTS_PLACEHOLDER not in body
        ):
            rendered = (
                f"{rendered.rstrip()}\n\n"
                f"ДОПОЛНИТЕЛЬНО ДЛЯ ЭТОГО ЗАПРОСА: верни ровно {count} вопросов "
                f"с квотой по уровням:\n{level_text}\n"
            )
        return rendered

    def active_response_schema(self, prompt_id: str) -> dict[str, Any]:
        prompt = self.get(prompt_id)
        schema = prompt.response_schema or default_question_prep_schema()
        return validate_response_schema(schema)

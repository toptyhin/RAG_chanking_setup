"""Parse LLM question-prep JSON and map quotes to chunk IDs."""

from __future__ import annotations

import copy
import json
import math
import re
from typing import Any

from pydantic import BaseModel, Field

from rageval_domain.query_type import resolve_query_type
from rageval_llm_providers.limits import estimate_tokens


class PreparedQuestion(BaseModel):
    text: str
    expected_answer: str | None = None
    source_quote: str | None = None
    evidence_quotes: list[str] = Field(default_factory=list)
    level: str | None = None
    query_type: str | None = None
    relevant_chunk_ids: list[str] = Field(default_factory=list)


QUESTION_PREP_TOTAL = 12
QUESTION_PREP_PER_LEVEL = 3
QUESTION_PREP_LEVELS: tuple[str, ...] = ("L1", "L2", "L3", "L4")
COMPLETION_RESERVE_TOKENS = 2048
# Our heuristic undercounts BPE tokenizers (esp. long Cyrillic prompts).
TOKEN_ESTIMATE_SAFETY = 1.4
# Extra slack so rendered prompts stay under provider max_context.
EXTRA_CONTEXT_MARGIN_TOKENS = 1024

# Sentence boundary: end punctuation + whitespace, then a new sentence start.
_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?…])"
    r"(?:[\"»”’)\]]*)"
    r"(?:\s+|\n+)"
    r"(?=[\"«“‘(\[]*[A-ZА-ЯЁ0-9])"
)
_WORD_SPLIT_RE = re.compile(r"(\s+)")

# Flat schema (no $ref) for Ollama ``format`` and OpenRouter structured outputs.
# ``additionalProperties: false`` is required for OpenRouter/OpenAI ``strict`` mode.
QUESTION_PREP_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "minItems": QUESTION_PREP_TOTAL,
            "maxItems": QUESTION_PREP_TOTAL,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": list(QUESTION_PREP_LEVELS),
                    },
                    "question": {"type": "string"},
                    "expected_answer": {"type": "string"},
                    "source_quote": {"type": "string"},
                    "evidence_quotes": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "level",
                    "question",
                    "expected_answer",
                    "source_quote",
                    "evidence_quotes",
                ],
            },
        }
    },
    "required": ["questions"],
}


def safe_estimate_tokens(text: str) -> int:
    """Conservative token estimate for context budgeting against providers."""
    raw = estimate_tokens(text)
    if raw <= 0:
        return 0
    return max(1, int(math.ceil(raw * TOKEN_ESTIMATE_SAFETY)))


def question_prep_schema(*, count: int | None = None) -> dict[str, Any]:
    """JSON Schema for question prep with a fixed ``questions`` array length."""
    n = QUESTION_PREP_TOTAL if count is None else int(count)
    if n < 1:
        raise ValueError("question count must be >= 1")
    schema = copy.deepcopy(QUESTION_PREP_JSON_SCHEMA)
    questions = schema["properties"]["questions"]
    questions["minItems"] = n
    questions["maxItems"] = n
    return schema


def format_level_counts(level_counts: dict[str, int]) -> str:
    lines: list[str] = []
    for level in QUESTION_PREP_LEVELS:
        lines.append(f"- {level}: {int(level_counts.get(level, 0))}")
    return "\n".join(lines)


def default_level_counts() -> dict[str, int]:
    return {level: QUESTION_PREP_PER_LEVEL for level in QUESTION_PREP_LEVELS}


def allocate_questions_across_parts(n_parts: int) -> list[dict[str, int]]:
    """Distribute 12 questions (3 per L1–L4) across ``n_parts`` LLM calls."""
    if n_parts < 1:
        raise ValueError("n_parts must be >= 1")
    if n_parts == 1:
        return [default_level_counts()]

    slots: list[str] = []
    for level in QUESTION_PREP_LEVELS:
        slots.extend([level] * QUESTION_PREP_PER_LEVEL)

    allocs = [{level: 0 for level in QUESTION_PREP_LEVELS} for _ in range(n_parts)]
    for index, level in enumerate(slots):
        allocs[index % n_parts][level] += 1
    return allocs


def part_question_count(level_counts: dict[str, int]) -> int:
    return sum(int(v) for v in level_counts.values())


def max_document_tokens(
    context_length: int,
    overhead_tokens: int,
    *,
    reserve: int = COMPLETION_RESERVE_TOKENS,
    margin: int = EXTRA_CONTEXT_MARGIN_TOKENS,
) -> int:
    """Tokens available for document text inside one LLM request."""
    return max(
        0,
        int(context_length) - int(overhead_tokens) - int(reserve) - int(margin),
    )


def split_into_sentences(text: str) -> list[tuple[str, str]]:
    """Return ``(separator_before, sentence)`` units; never cuts inside a word.

    ``separator_before`` is ``""`` for the first unit, ``" "`` between sentences
    in a paragraph, and ``"\\n\\n"`` at paragraph boundaries.
    """
    text = (text or "").strip()
    if not text:
        return []

    units: list[tuple[str, str]] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for para_index, para in enumerate(paragraphs):
        sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(para) if s.strip()]
        if not sentences:
            sentences = [para]
        for sent_index, sentence in enumerate(sentences):
            if para_index == 0 and sent_index == 0:
                sep = ""
            elif sent_index == 0:
                sep = "\n\n"
            else:
                sep = " "
            units.append((sep, sentence))
    return units


def _split_oversized_sentence(sentence: str, max_tokens: int) -> list[str]:
    """Split one oversized sentence on whitespace only (word-safe)."""
    sentence = sentence.strip()
    if not sentence:
        return []
    if safe_estimate_tokens(sentence) <= max_tokens:
        return [sentence]

    pieces = [p for p in _WORD_SPLIT_RE.split(sentence) if p != ""]
    parts: list[str] = []
    current = ""
    for piece in pieces:
        candidate = current + piece
        if current and safe_estimate_tokens(candidate) > max_tokens:
            stripped = current.strip()
            if stripped:
                parts.append(stripped)
            current = "" if piece.isspace() else piece
            # Pathological single token longer than budget.
            while current and safe_estimate_tokens(current) > max_tokens:
                lo, hi = 1, len(current)
                best = 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if safe_estimate_tokens(current[:mid]) <= max_tokens:
                        best = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1
                parts.append(current[:best])
                current = current[best:]
        else:
            current = candidate
    if current.strip():
        parts.append(current.strip())
    return [p for p in parts if p]


def split_text_by_token_budget(text: str, max_tokens: int) -> list[str]:
    """Split document on finished sentences so each part fits ``max_tokens``."""
    text = (text or "").strip()
    if not text:
        return []
    if max_tokens < 32:
        raise ValueError(
            f"token budget for document part is too small ({max_tokens}); "
            "use a model with a larger context window"
        )
    if safe_estimate_tokens(text) <= max_tokens:
        return [text]

    units = split_into_sentences(text)
    parts: list[str] = []
    current = ""

    for sep, sentence in units:
        if safe_estimate_tokens(sentence) > max_tokens:
            if current.strip():
                parts.append(current.strip())
                current = ""
            parts.extend(_split_oversized_sentence(sentence, max_tokens))
            continue

        candidate = sentence if not current else current + sep + sentence
        if current and safe_estimate_tokens(candidate) > max_tokens:
            parts.append(current.strip())
            current = sentence
        else:
            current = candidate

    if current.strip():
        parts.append(current.strip())
    return [p for p in parts if p]


def plan_document_parts(
    document: str,
    *,
    overhead_tokens: int,
    context_length: int | None,
    reserve: int = COMPLETION_RESERVE_TOKENS,
) -> list[str]:
    """Return one or more document slices that fit the model context."""
    document = (document or "").strip()
    if not document:
        return []
    if context_length is None or context_length <= 0:
        return [document]

    # Overhead is measured on an empty-document render; inflate it the same way.
    safe_overhead = max(
        overhead_tokens,
        int(math.ceil(overhead_tokens * TOKEN_ESTIMATE_SAFETY)),
    )
    budget = max_document_tokens(
        context_length,
        safe_overhead,
        reserve=reserve,
    )
    if budget < 32:
        raise ValueError(
            f"Model context ({context_length}) is too small for question prep "
            f"(overhead≈{safe_overhead}, reserve={reserve}, "
            f"margin={EXTRA_CONTEXT_MARGIN_TOKENS})"
        )
    parts = split_text_by_token_budget(document, budget)
    if len(parts) > QUESTION_PREP_TOTAL:
        raise ValueError(
            f"Document needs ~{len(parts)} context windows, but question prep "
            f"allows at most {QUESTION_PREP_TOTAL} parts "
            f"(12 questions / 3 per L1–L4). Use a model with a larger context."
        )
    return parts


def select_balanced_questions(
    questions: list[PreparedQuestion],
    *,
    per_level: int = QUESTION_PREP_PER_LEVEL,
    total: int = QUESTION_PREP_TOTAL,
) -> list[PreparedQuestion]:
    """Keep up to ``per_level`` questions per L1–L4 (target ``total``)."""
    by_level: dict[str, list[PreparedQuestion]] = {
        level: [] for level in QUESTION_PREP_LEVELS
    }
    other: list[PreparedQuestion] = []
    seen: set[str] = set()
    for question in questions:
        key = re.sub(r"\s+", " ", question.text).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        level = (question.level or "").strip().upper()
        if level in by_level:
            by_level[level].append(question)
        else:
            other.append(question)

    selected: list[PreparedQuestion] = []
    for level in QUESTION_PREP_LEVELS:
        selected.extend(by_level[level][:per_level])

    leftovers: list[PreparedQuestion] = []
    for level in QUESTION_PREP_LEVELS:
        leftovers.extend(by_level[level][per_level:])
    leftovers.extend(other)

    need = max(0, total - len(selected))
    selected.extend(leftovers[:need])
    return selected[:total]


_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

# LLM sometimes wraps JSON string values in typographic quotes instead of ".
# Match only after a JSON key colon (`"key":`) or array punctuation — not after
# narrative colons inside already-quoted strings (`"текст: «цитата»"`).
_TYPOGRAPHIC_VALUE_RE = re.compile(
    r'(?P<prefix>"\s*:|[,[])(?P<ws>\s*)'
    r'(?:«(?P<a>[^»]*)»|“(?P<b>[^”]*)”|„(?P<c>[^“]*)“)',
    re.DOTALL,
)

# Pretty-printed rows like `"expected_answer": Чудило,` (no JSON quotes).
# Keep colon-trailing whitespace in its own group and require `\S` so the
# lookahead cannot backtrack into `"key": [` / `"key": "…"`.
_BARE_LINE_VALUE_RE = re.compile(
    r'^(\s*"[^"]+"\s*:)(\s*)'
    r'(?!true\b|false\b|null\b|"|\{|\[|-?\d)'
    r'(\S.*?)(,?)\s*$',
    re.MULTILINE,
)

_BAD_KEY_FIXES: tuple[tuple[str, str], ...] = (
    ('"expected answer"', '"expected_answer"'),
)


def _escape_json_string_content(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def normalize_typographic_json_quotes(text: str) -> str:
    """Turn «...» / “...” / „...“ used as JSON value delimiters into "..."."""

    def _repl(match: re.Match[str]) -> str:
        inner = match.group("a") or match.group("b") or match.group("c") or ""
        return (
            f'{match.group("prefix")}{match.group("ws")}'
            f'"{_escape_json_string_content(inner)}"'
        )

    return _TYPOGRAPHIC_VALUE_RE.sub(_repl, text)


def quote_bare_json_line_values(text: str) -> str:
    """Quote unquoted scalar values on pretty-printed ``"key": value`` lines."""

    def _repl(match: re.Match[str]) -> str:
        prefix, ws, inner, comma = (
            match.group(1),
            match.group(2),
            match.group(3).strip(),
            match.group(4),
        )
        if (
            inner.startswith("«")
            and inner.endswith("»")
            and inner.count("«") == 1
        ):
            inner = inner[1:-1]
        return f'{prefix}{ws}"{_escape_json_string_content(inner)}"{comma}'

    return _BARE_LINE_VALUE_RE.sub(_repl, text)


def repair_llm_json_text(text: str) -> str:
    """Best-effort fixes for common LLM JSON mistakes (Nemotron/OpenRouter)."""
    fixed = text
    for old, new in _BAD_KEY_FIXES:
        fixed = fixed.replace(old, new)
    fixed = normalize_typographic_json_quotes(fixed)
    fixed = quote_bare_json_line_values(fixed)
    return fixed


def _loads_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fixed = repair_llm_json_text(text)
        if fixed != text:
            return json.loads(fixed)
        raise


def extract_json_payload(raw: str) -> Any:
    """Best-effort extract of a JSON value from an LLM reply."""
    text = raw.strip()
    if not text:
        raise ValueError("empty LLM response")

    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return _loads_json(text)
    except json.JSONDecodeError:
        pass

    start_obj = text.find("{")
    start_arr = text.find("[")
    starts = [i for i in (start_obj, start_arr) if i >= 0]
    if not starts:
        raise ValueError("LLM response does not contain JSON")
    start = min(starts)
    end_obj = text.rfind("}")
    end_arr = text.rfind("]")
    end = max(end_obj, end_arr)
    if end <= start:
        raise ValueError("LLM response JSON looks truncated")
    return _loads_json(text[start : end + 1])


def _as_question_dicts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("questions", "items", "queries", "data"):
            inner = payload.get(key)
            if isinstance(inner, list):
                payload = inner
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("expected a JSON array of questions")
    out: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str) and item.strip():
            out.append({"question": item.strip()})
    if not out:
        raise ValueError("no questions found in LLM response")
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def match_chunks_for_quote(
    quote: str | None,
    chunks: list[tuple[str, str]],
    *,
    limit: int = 3,
) -> list[str]:
    """Return chunk_ids whose text best overlaps the quote."""
    if not quote or not chunks:
        return []
    needle = _norm(quote)
    if len(needle) < 8:
        return []

    scored: list[tuple[int, str]] = []
    for chunk_id, text in chunks:
        hay = _norm(text)
        if not hay:
            continue
        score = 0
        if needle in hay or hay in needle:
            score = min(len(needle), len(hay))
        else:
            # token overlap fallback
            n_tokens = set(needle.split())
            h_tokens = set(hay.split())
            if not n_tokens or not h_tokens:
                continue
            overlap = len(n_tokens & h_tokens)
            if overlap >= max(3, len(n_tokens) // 2):
                score = overlap
        if score > 0:
            scored.append((score, chunk_id))

    scored.sort(key=lambda x: (-x[0], x[1]))
    seen: set[str] = set()
    result: list[str] = []
    for _, cid in scored:
        if cid in seen:
            continue
        seen.add(cid)
        result.append(cid)
        if len(result) >= limit:
            break
    return result


def parse_prepared_questions(
    raw: str,
    chunks: list[tuple[str, str]] | None = None,
) -> list[PreparedQuestion]:
    payload = extract_json_payload(raw)
    items = _as_question_dicts(payload)
    chunk_pairs = chunks or []
    questions = [
        q
        for item in items
        if (q := _prepared_question_from_item(item, chunk_pairs)) is not None
    ]
    if not questions:
        raise ValueError("parsed LLM JSON but found no usable questions")
    return questions


def _prepared_question_from_item(
    item: dict[str, Any],
    chunk_pairs: list[tuple[str, str]],
) -> PreparedQuestion | None:
    text = (
        item.get("question")
        or item.get("text")
        or item.get("query")
        or ""
    )
    if not isinstance(text, str) or not text.strip():
        return None
    expected = item.get("expected_answer") or item.get("answer")
    quote = item.get("source_quote") or item.get("quote") or expected
    level = item.get("level")
    level_str = level.strip() if isinstance(level, str) else None
    explicit_type = item.get("query_type") or item.get("type")
    query_type = resolve_query_type(
        query_type=explicit_type if isinstance(explicit_type, str) else None,
        level=level_str,
    )
    evidence_quotes = _evidence_quotes_from_item(item)
    relevant = _relevant_ids_for_quotes(
        evidence_quotes or ([quote] if isinstance(quote, str) else []),
        chunk_pairs,
    )
    return PreparedQuestion(
        text=text.strip(),
        expected_answer=expected.strip() if isinstance(expected, str) else None,
        source_quote=quote.strip() if isinstance(quote, str) else None,
        evidence_quotes=evidence_quotes,
        level=level_str,
        query_type=query_type,
        relevant_chunk_ids=relevant,
    )


def _evidence_quotes_from_item(item: dict[str, Any]) -> list[str]:
    evidence_quotes: list[str] = []
    raw_eq = item.get("evidence_quotes") or item.get("evidence") or []
    if not isinstance(raw_eq, list):
        return evidence_quotes
    for eq in raw_eq:
        if isinstance(eq, str) and eq.strip():
            evidence_quotes.append(eq.strip())
    return evidence_quotes


def _relevant_ids_for_quotes(
    quotes: list[str],
    chunk_pairs: list[tuple[str, str]],
) -> list[str]:
    relevant: list[str] = []
    seen_rel: set[str] = set()
    for qtext in quotes:
        for cid in match_chunks_for_quote(qtext, chunk_pairs):
            if cid not in seen_rel:
                seen_rel.add(cid)
                relevant.append(cid)
    return relevant

"""Document split / question allocation for multi-pass prep."""

from __future__ import annotations

from rageval_llm_providers.question_prep import (
    QUESTION_PREP_TOTAL,
    PreparedQuestion,
    allocate_questions_across_parts,
    part_question_count,
    plan_document_parts,
    question_prep_schema,
    safe_estimate_tokens,
    select_balanced_questions,
    split_into_sentences,
    split_text_by_token_budget,
)


def test_question_prep_schema_count() -> None:
    schema = question_prep_schema(count=4)
    assert schema["properties"]["questions"]["minItems"] == 4
    assert schema["properties"]["questions"]["maxItems"] == 4


def test_allocate_three_parts_sums_to_twelve() -> None:
    allocs = allocate_questions_across_parts(3)
    assert len(allocs) == 3
    assert sum(part_question_count(a) for a in allocs) == QUESTION_PREP_TOTAL
    totals = {"L1": 0, "L2": 0, "L3": 0, "L4": 0}
    for alloc in allocs:
        for level, n in alloc.items():
            totals[level] += n
    assert totals == {"L1": 3, "L2": 3, "L3": 3, "L4": 3}


def test_split_into_sentences_keeps_boundaries() -> None:
    text = (
        "Первое предложение. Второе предложение!\n\n"
        "Третье после абзаца? И ещё одно."
    )
    units = split_into_sentences(text)
    sentences = [s for _, s in units]
    assert sentences == [
        "Первое предложение.",
        "Второе предложение!",
        "Третье после абзаца?",
        "И ещё одно.",
    ]
    assert units[2][0] == "\n\n"


def test_split_text_respects_budget_and_sentences() -> None:
    sentences = [
        f"Это законченное предложение номер {i} про возврат товара."
        for i in range(40)
    ]
    text = " ".join(sentences)
    budget = max(40, safe_estimate_tokens(text) // 4)
    parts = split_text_by_token_budget(text, budget)
    assert len(parts) >= 2
    for part in parts:
        assert safe_estimate_tokens(part) <= budget
        assert part[-1] in ".!?"


def test_plan_document_parts_single_when_fits() -> None:
    parts = plan_document_parts(
        "short document",
        overhead_tokens=100,
        context_length=8000,
    )
    assert parts == ["short document"]


def test_plan_document_parts_splits_when_needed() -> None:
    text = ("Абзац с текстом про возврат товара и доставку. " * 60 + "\n\n") * 30
    overhead = 500
    # Enough for several mid-size parts, not the whole document.
    ctx = 12_000
    parts = plan_document_parts(
        text,
        overhead_tokens=overhead,
        context_length=ctx,
    )
    assert 2 <= len(parts) <= 12


def test_plan_document_parts_rejects_too_many_windows() -> None:
    text = ("Это отдельное предложение про возврат. " * 80 + "\n\n") * 40
    try:
        plan_document_parts(text, overhead_tokens=1000, context_length=8_000)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        msg = str(exc)
        assert "at most 12 parts" in msg or "too small" in msg


def test_select_balanced_questions() -> None:
    qs = [
        PreparedQuestion(text=f"q-{level}-{i}", level=level)
        for level in ("L1", "L2", "L3", "L4")
        for i in range(5)
    ]
    selected = select_balanced_questions(qs)
    assert len(selected) == 12
    counts = {"L1": 0, "L2": 0, "L3": 0, "L4": 0}
    for q in selected:
        assert q.level is not None
        counts[q.level] += 1
    assert counts == {"L1": 3, "L2": 3, "L3": 3, "L4": 3}

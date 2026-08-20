"""Parse LLM question-prep JSON into drafts."""

from __future__ import annotations

import pytest

from rageval_llm_providers.question_prep import (
    QUESTION_PREP_JSON_SCHEMA,
    extract_json_payload,
    match_chunks_for_quote,
    parse_prepared_questions,
)


def test_extract_json_from_fenced_reply() -> None:
    raw = """Sure!

```json
[{"question": "Q1", "expected_answer": "A1", "level": "L1", "source_quote": "hello world"}]
```
"""
    payload = extract_json_payload(raw)
    assert isinstance(payload, list)
    assert payload[0]["question"] == "Q1"


def test_parse_wrapped_questions_object() -> None:
    raw = """{
  "questions": [
    {
      "level": "L1",
      "question": "How long?",
      "expected_answer": "30 days",
      "source_quote": "return within 30 days",
      "evidence_quotes": ["return within 30 days"]
    }
  ]
}"""
    questions = parse_prepared_questions(raw)
    assert len(questions) == 1
    assert questions[0].text == "How long?"
    assert questions[0].evidence_quotes == ["return within 30 days"]
    assert QUESTION_PREP_JSON_SCHEMA["required"] == ["questions"]


def test_parse_and_match_chunks() -> None:
    raw = """[
  {
    "level": "L2",
    "question": "What is the return window?",
    "expected_answer": "30 days",
    "source_quote": "Customers may return items within 30 days of purchase."
  },
  {
    "question": "Support hours?",
    "expected_answer": "9-18",
    "source_quote": "Support is available 9-18 on weekdays."
  }
]
"""
    chunks = [
        ("c_return", "Customers may return items within 30 days of purchase."),
        ("c_support", "Support is available 9-18 on weekdays."),
        ("c_other", "Unrelated warranty text."),
    ]
    questions = parse_prepared_questions(raw, chunks)
    assert len(questions) == 2
    assert questions[0].relevant_chunk_ids == ["c_return"]
    assert questions[1].relevant_chunk_ids == ["c_support"]
    assert questions[0].level == "L2"
    assert questions[0].query_type == "l2"
    assert questions[1].query_type is None


def test_parse_explicit_query_type() -> None:
    raw = '[{"question": "Q?", "expected_answer": "A", "query_type": "factoid", "level": "L9"}]'
    questions = parse_prepared_questions(raw)
    assert questions[0].query_type == "factoid"
    assert questions[0].level == "L9"
    assert match_chunks_for_quote("hi", [("c1", "hi there")]) == []


def test_parse_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_prepared_questions("[]")


def test_parse_guillemet_delimited_source_quote() -> None:
    """Nemotron-style: source_quote wrapped in «...» instead of JSON quotes."""
    raw = """{
  "questions": [
    {
      "level": "L4",
      "question": "Как изменилось отношение экипажа к еде?",
      "expected_answer": "Еда стала единственной ценностью.",
      "source_quote": «Как ни позорно, но все, зачем мы живем — это еда.»,
      "evidence_quotes": [
        "Как ни позорно, но все, зачем мы живем — это еда.",
        "Появились даже некоторые весьма рискованные шутки на тему каннибализма."
      ]
    }
  ]
}"""
    questions = parse_prepared_questions(raw)
    assert len(questions) == 1
    assert questions[0].source_quote == (
        "Как ни позорно, но все, зачем мы живем — это еда."
    )
    assert questions[0].evidence_quotes[0].startswith("Как ни позорно")


def test_guillemets_inside_valid_json_string_untouched() -> None:
    raw = (
        '[{"question": "Q?", "expected_answer": "A", '
        '"source_quote": "Текст с «кавычками» внутри", '
        '"evidence_quotes": ["Текст с «кавычками» внутри"]}]'
    )
    questions = parse_prepared_questions(raw)
    assert questions[0].source_quote == "Текст с «кавычками» внутри"


def test_parse_nemotron_bare_expected_answers() -> None:
    """Nemotron free: guillemets, bare scalars, spaced key, guillemets in quotes."""
    raw = """{
  "questions": [
    {
      "level": "L1",
      "question": "Как назывался корабль?",
      "expected_answer": «Эндьюранс»,
      "source_quote": "Корабль назывался «Эндьюранс».",
      "evidence_quotes": [
        "Корабль назывался «Эндьюранс»."
      ]
    },
    {
      "level": "L2",
      "question": "Какое прозвище получил Уорсли?",
      "expected_answer": Чудило,
      "source_quote": "Фрэнк Уорсли, которого все звали Чудило.",
      "evidence_quotes": [
        "Фрэнк Уорсли, которого все звали Чудило."
      ]
    },
    {
      "level": "L3",
      "question": "Что было в записке?",
      "expected answer": Шеклтон сообщил, что «Эндьюранс» разбилась,
      "source_quote": "В записке сообщалось, что «Эндьюранс» разбилась.",
      "evidence_quotes": [
        "В конце сообщения были слова: «Все в порядке»."
      ]
    }
  ]
}"""
    questions = parse_prepared_questions(raw)
    assert len(questions) == 3
    assert questions[0].expected_answer == "Эндьюранс"
    assert questions[1].expected_answer == "Чудило"
    assert questions[2].expected_answer == (
        "Шеклтон сообщил, что «Эндьюранс» разбилась"
    )
    assert "«Все в порядке»" in questions[2].evidence_quotes[0]

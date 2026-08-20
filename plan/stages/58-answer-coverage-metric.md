# Этап 58. Метрика answer-coverage (покрытие ожидаемого ответа)

**Slug:** `answer-coverage-metric`
**Статус:** done
**Приоритет:** P2 (методология оценки)

## Проблема

Сейчас релевантность и все метрики завязаны только на `chunk_id`
(`metrics.py`, `relevance.py`). Но у подготовленных вопросов есть `expected_answer`
и `source_quote` (`question_prep.py:12-17`), которые в retrieval-оценке не
используются. Recall@k отвечает «нашёлся ли размеченный чанк», но не «содержится ли
фактический ответ в извлечённом контексте» — а это ближе к тому, что увидит LLM.

`TestQuery` не хранит `expected_answer` (artifacts.py:121-132) — есть только
`query_type` и `meta`.

## Цель

Добавить retrieval-метрику answer-coverage: доля запросов, где `expected_answer`
(или `source_quote`) фактически присутствует в тексте top-k извлечённых чанков.
Это дешёвый мост к e2e faithfulness без запуска LLM.

## В scope

- `TestQuery`: хранить `expected_answer` / `source_quote` (поле или через `meta`;
  при импорте test_set из prepared questions — заполнять).
- `packages/eval`: функция `answer_coverage_at_k(expected, chunk_texts_topk)`
  через нормализованный substring / token-overlap (переиспользовать логику
  `match_chunks_for_quote`).
- `eval_point.py`: считать `answer_coverage@k` и класть в metrics row.
- Отчёт: колонка answer-coverage рядом с Recall/nDCG.

## Вне scope

- LLM-судья faithfulness (это e2e-слой, later).
- Семантическое совпадение ответа (только лексическое покрытие в этом этапе).

## Результат (deliverables)

- Правки `domain/artifacts.py`, `packages/eval/...`, `eval_point.py`, report.
- Тест: чанк с ответом в top-k → coverage=1; без — 0.

## Критерии готовности

- Метрика видна в таблице и отчёте.
- Импорт prepared questions заполняет `expected_answer`.

## Зависит от

- [24. Метрика Recall@k](./24-metrics-recall.md)
- [18. Импорт test_set](./18-testset-import.md)

## Документация

- `evaluation-axes.md §2.5` (groundedness), `§4`
- `ARCHITECTURE.md §7.7`

## Оценка сложности

M.

# Этап 60. Закалка test_set: типы запросов, no-answer, hard-negatives

**Slug:** `testset-hardening`
**Статус:** done
**Приоритет:** P2 (методология оценки)

## Проблема

`evaluation-axes.md §2.6` требует типизацию запросов, явные no-answer кейсы и
hard-negatives как обязательную ось методологии. Сейчас `TestQuery.query_type`
существует (artifacts.py:131), но не используется в метриках/отчёте; no-answer и
hard-negatives не моделируются. Оценка по одному вопросу или по нетипизированному
набору гоняется за шумом и завышает Recall.

## Цель

Поддержать типы запросов и no-answer/hard-negatives в генерации/импорте, метриках
и разбивке отчёта, чтобы вывод «какую настройку брать» опирался на стабильный
golden core, а не на один вопрос.

## В scope

- Типы: factoid / multi-hop / ambiguous / out-of-domain / no-answer (в `query_type`).
- No-answer: запрос с пустым `relevant_chunk_ids`; метрика корректно трактует
  «правильно ничего не вернуть» (abstention/precision вместо recall).
- Hard-negatives: пометка близких, но нерелевантных чанков (в `meta`) для будущих
  метрик точности.
- Отчёт/метрики: разбивка Recall/nDCG по `query_type` (breakdown в report).
- Генерация/импорт: сохранять `query_type`; для prepared questions — из поля `level`
  (`question_prep.py:16`).

## Вне scope

- LLM-генерация большого синтетического набора (отдельный этап testgen).
- Adversarial-атаки как отдельная категория (later).

## Результат (deliverables)

- Правки импорта test_set, `eval` (breakdown), report.
- Тест: no-answer запрос не портит агрегированный Recall; отчёт показывает
  метрики по типам.

## Критерии готовности

- В отчёте есть разбивка по `query_type`.
- No-answer кейсы обрабатываются отдельной логикой, а не как recall=0.

## Зависит от

- [18. Импорт test_set](./18-testset-import.md)
- [48. HTML отчёт](./48-html-report.md)
- [59. Верификация разметки + graded relevance](./59-relevance-review-graded.md)

## Документация

- `evaluation-axes.md §2.6`
- `evaluation-flows.md §7`

## Оценка сложности

M.

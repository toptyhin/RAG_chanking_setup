# Этап 59. Верификация разметки + graded relevance

**Slug:** `relevance-review-graded`
**Статус:** done
**Приоритет:** P2 (методология оценки)

## Проблема

1. `relevant_chunk_ids` формируются **автоматически**: `match_chunks_for_quote`
   по overlap цитаты с чанками, лимит 3 (`question_prep.py:78-121`). Без ручной
   проверки метрика меряет качество матчинга цитат, а не retrieval.
2. `ndcg_at_k` использует бинарную релевантность (`metrics.py:18-31`), хотя
   `match_chunks_for_quote` уже возвращает score с ранжированием — градации теряются.

## Цель

Дать возможность подтвердить/поправить авторазметку и поддержать градуированную
релевантность (например primary=2, secondary=1) в nDCG.

## В scope

- Пометка провенанса разметки: `auto` vs `verified` (в `TestQuery.meta`).
- API/UI: просмотр и правка `relevant_chunk_ids` перед запуском run (минимум — API).
- `TestQuery`: опциональные веса релевантности (grade per chunk_id).
- `ndcg_at_k`: принимать graded relevance (gain = grade), сохранив бинарный дефолт.
- `resolve_relevance`: пробрасывать градации.

## Вне scope

- Полноценный разметочный UI-редактор (later, отдельный этап UI).
- Межаннотаторное согласие.

## Результат (deliverables)

- Правки `domain/artifacts.py`, `packages/eval/metrics.py`, `relevance.py`,
  API test_set.
- Тест: graded nDCG выше при правильном порядке primary/secondary; бинарный режим
  не меняет поведение существующих тестов.

## Критерии готовности

- Можно пометить test_set как `verified`.
- nDCG учитывает градации, когда они заданы.

## Зависит от

- [25. Метрика nDCG@k](./25-metrics-ndcg.md)
- [18. Импорт test_set](./18-testset-import.md)
- [58. Метрика answer-coverage](./58-answer-coverage-metric.md)

## Документация

- `evaluation-axes.md §2.6`
- `evaluation-flows.md §7` (правила test_set)

## Оценка сложности

M.

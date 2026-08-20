# Этап 23. Dense retrieval + latency

**Slug:** `dense-retrieve`  
**Статус:** done

## Цель

Поиск по вопросам test_set.

## В scope

- encode queries
- search
- p50/p95 latency

## Вне scope

- rerank
- sparse

## Результат (deliverables)

- packages/retrieval dense

## Критерии готовности

- для каждого query есть ranked chunk_ids + latency stats

## Зависит от

- [22. Index service без квантования](./22-index-service-basic.md)
- [18. Импорт test_set](./18-testset-import.md)

## Документация

- `ARCHITECTURE.md §7.5`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

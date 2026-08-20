# Этап 39. Rerank on/off

**Slug:** `rerank-cross-encoder`  
**Статус:** done

## Цель

Cross-encoder на кандидатах.

## В scope

- одна маленькая cross-encoder модель
- top_n → keep
- ось rerank.enabled

## Вне scope

- LLM rerank

## Результат (deliverables)

- packages/rerank

## Критерии готовности

- с rerank порядок top меняется на фикстуре; latency растёт

## Зависит от

- [23. Dense retrieval + latency](./23-dense-retrieve.md)
- [19. Embedding: один локальный моделью](./19-embedding-service.md)

## Документация

- `ARCHITECTURE.md §7.6`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

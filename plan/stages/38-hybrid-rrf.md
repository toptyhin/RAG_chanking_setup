# Этап 38. Hybrid RRF

**Slug:** `hybrid-rrf`  
**Статус:** done

## Цель

Слияние dense + sparse.

## В scope

- RRF fusion
- флаг retrieval.mode=hybrid

## Вне scope

- веса обучения

## Результат (deliverables)

- packages/retrieval hybrid

## Критерии готовности

- режим hybrid доступен в orchestrator swept

## Зависит от

- [37. Sparse BM25](./37-sparse-bm25.md)
- [23. Dense retrieval + latency](./23-dense-retrieve.md)
- [30. Сетка swept (2 оси максимум)](./30-orchestrator-grid.md)

## Документация

- `evaluation-axes.md hybrid`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

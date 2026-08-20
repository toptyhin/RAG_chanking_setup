# Этап 56. Кеш sparse BM25 индекса по chunk_set

**Slug:** `sparse-index-cache`
**Статус:** done
**Приоритет:** P1 (стоимость прогонов)

## Проблема

В `evaluate_retrieval_point` при mode ∈ {sparse, hybrid} и отсутствии переданного
индекса вызывается `SparseBm25Index.build(chunk_set)` на **каждой** точке grid
(`eval_point.py:117-118`). При фиксированном `chunk_set` индекс идентичен между
точками, но перестраивается заново — лишний токенайз + индексация на каждый sweep
по quant/dim/rerank.

`SparseBm25Index` уже умеет `save`/`load` на диск (sparse.py:38-50) — механизм есть,
но не используется в оркестраторе.

## Цель

Строить BM25 индекс один раз на `chunk_set` в рамках run и переиспользовать между
точками; опционально кешировать на диск по ключу `chunk_set_id`.

## В scope

- Оркестратор: построить `SparseBm25Index` один раз перед сеткой (если какой-либо
  point использует sparse/hybrid) и передавать в `evaluate_retrieval_point`.
- Опциональный дисковый кеш `cache_fs`: ключ `chunk_set_id` → каталог BM25.
- Инвалидация: кеш привязан к неизменяемому `chunk_set_id` (артефакты immutable).

## Вне scope

- Тюнинг BM25 (k1/b) — отдельная ось при необходимости.
- Распараллеливание точек.

## Результат (deliverables)

- Правка оркестратора (grid runner) + `eval_point.py` (использовать переданный индекс).
- Опциональный адаптер кеша.
- Тест: при grid из N точек с hybrid `SparseBm25Index.build` вызывается один раз.

## Критерии готовности

- Время sparse/hybrid sweep падает: индекс строится 1 раз, не N раз.
- Результаты идентичны прежним (тот же индекс).

## Зависит от

- [37. Sparse BM25](./37-sparse-bm25.md)
- [38. Hybrid RRF](./38-hybrid-rrf.md)
- [30. Сетка swept (2 оси максимум)](./30-orchestrator-grid.md)

## Документация

- `ARCHITECTURE.md §14` (кеширование)
- `evaluation-flows.md §8`

## Оценка сложности

S–M.

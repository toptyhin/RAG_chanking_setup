# Этап 55. Ось HNSW-параметров (m / ef_construct / ef_search)

**Slug:** `hnsw-params-axis`
**Статус:** done
**Приоритет:** P1 (расширение оси сравнения)

## Проблема

`IndexRun.hnsw` — уже существующее поле (artifacts.py:165), но оно нигде не
заполняется и не прокидывается: `recreate_collection` создаёт коллекцию с
дефолтами Qdrant (`client.py:98-102`), а `search` не задаёт `ef_search`.
`evaluation-axes.md §2.1` заявляет HNSW-параметры как ось trade-off
точность ↔ скорость, но её нет.

## Цель

Сделать `m` / `ef_construct` (build) и `ef_search` (query) настраиваемыми осями,
записывать их в `IndexRun.hnsw`, прокидывать в Qdrant.

## В scope

- `client.recreate_collection`: принять `hnsw_config` → `qm.HnswConfigDiff(m, ef_construct)`.
- `client.search`: принять `ef_search` → `qm.SearchParams(hnsw_ef=...)`
  (совместимо с уже прокидываемым `quantization`-rescore в тех же `SearchParams`).
- `build_index` / `eval_point`: оси `index.hnsw.m`, `index.hnsw.ef_construct`,
  `retrieval.ef_search`; заполнять `IndexRun.hnsw`.
- Дефолты: сохранить текущее поведение Qdrant, если ось не задана.

## Вне scope

- Автотюнинг HNSW.
- `on_disk` payload/vectors как отдельная ось.

## Результат (deliverables)

- Правки `client.py`, `packages/index/...`, `eval_point.py`.
- Тест: два `index_run` с разными `m`/`ef_construct` отличаются `hnsw` в артефакте;
  разные `ef_search` дают разный latency/recall на фикстуре.

## Критерии готовности

- `IndexRun.hnsw` заполнен реальными значениями.
- Ось видна в Pareto как отдельный trade-off точность↔latency.

## Зависит от

- [21. Адаптер Qdrant: CRUD коллекции](./21-qdrant-adapter.md)
- [22. Index service без квантования](./22-index-service-basic.md)
- [23. Dense retrieval + latency](./23-dense-retrieve.md)

## Документация

- `evaluation-axes.md §2.1`
- `ARCHITECTURE.md §7.4`

## Оценка сложности

M.

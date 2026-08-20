# Этап 22. Index service без квантования

**Slug:** `index-service-basic`  
**Статус:** done

## Цель

Построить index_run из chunk_set + embeddings.

## В scope

- создать коллекцию
- залить векторы
- сохранить meta index_run
- замер build_time

## Вне scope

- quant, HNSW tuning UI

## Результат (deliverables)

- packages/index

## Критерии готовности

- index_run появляется в registry, search по коллекции работает

## Зависит от

- [20. FS cache эмбеддингов](./20-embedding-cache.md)
- [21. Адаптер Qdrant: CRUD коллекции](./21-qdrant-adapter.md)
- [17. Сохранение chunk_set из reference](./17-persist-chunk-set.md)

## Документация

- `ARCHITECTURE.md §7.4`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

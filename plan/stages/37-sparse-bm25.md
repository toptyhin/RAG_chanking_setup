# Этап 37. Sparse BM25

**Slug:** `sparse-bm25`  
**Статус:** done

## Цель

Лексический поиск по chunk_set.

## В scope

- bm25s индекс в памяти/на диске
- search top_k

## Вне scope

- hybrid

## Результат (deliverables)

- packages/retrieval sparse

## Критерии готовности

- по точному термину находит нужный chunk

## Зависит от

- [17. Сохранение chunk_set из reference](./17-persist-chunk-set.md)

## Документация

- `DEPENDENCIES.md bm25s`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 20. FS cache эмбеддингов

**Slug:** `embedding-cache`  
**Статус:** done

## Цель

Не пересчитывать векторы повторно.

## В scope

- ключ chunk_set+model+dim
- запись/чтение numpy/jsonl на диске
- cache hit path

## Вне scope

- кеш prep/chunk

## Результат (deliverables)

- adapters/cache_fs

## Критерии готовности

- второй encode того же chunk_set не вызывает модель (мок/счётчик)

## Зависит от

- [19. Embedding: один локальный моделью](./19-embedding-service.md)
- [07. ObjectStore: локальный FS](./07-object-store-fs.md)

## Документация

- `ARCHITECTURE.md §14`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

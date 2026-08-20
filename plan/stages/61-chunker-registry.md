# Этап 61. Chunker registry + unified options

**Slug:** `chunker-registry`  
**Статус:** done

## Цель

Единый интерфейс чанкинга: protocol, дискриминированные options, registry с ленивой загрузкой, reference adapter.

## В scope

- `Chunker` protocol
- options union (semchunk / chunklet / reference_fixed)
- registry: list_providers, get_chunker, ensure_provider
- token_counters (words / chars / tiktoken lazy)
- reference adapter → существующий `chunk_fixed_size`
- публичный `chunk_corpus`

## Вне scope

- adapters сторонних библиотек (этап 62)
- UI (этап 63)

## Результат (deliverables)

- `packages/chunking` registry + options + reference adapter
- unit-тесты registry / reference через `chunk_corpus`

## Критерии готовности

- `chunk_corpus(corpus, ReferenceOptions(...))` даёт тот же pipeline_id, что и `chunk_fixed_size`
- `list_providers()` возвращает порядок: semchunk → chunklet → reference_fixed
- lazy ensure не импортирует сторонние пакеты до вызова

## Зависит от

- [15. Reference chunker](./15-chunk-reference.md)

## Оценка сложности

M

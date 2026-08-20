# Этап 62. Library adapters + unified chunk API

**Slug:** `chunker-library-adapters`  
**Статус:** done

## Цель

Адаптеры semchunk / chunklet (document+code) / reference_fixed, optional deps, API `GET /chunkers` и `POST /chunk-sets`.

## В scope

- adapters semchunk / chunklet / reference_fixed
- extras `chunkers` в pyproject / requirements
- API endpoints
- unit + API tests

## Вне scope

- UI (этап 63)
- Isaacus AI

## Результат (deliverables)

- работающие провайдеры через `chunk_corpus`
- REST для каталога и создания chunk_set

## Критерии готовности

- каждый доступный provider даёт chunk_set
- недоступный optional package → available=false / 503
- старый `POST .../reference` работает

## Зависит от

- [61. Chunker registry](./61-chunker-registry.md)

## Оценка сложности

L

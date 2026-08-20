# Этап 21. Адаптер Qdrant: CRUD коллекции

**Slug:** `qdrant-adapter`  
**Статус:** done

## Цель

Создать коллекцию, upsert, search, delete.

## В scope

- qdrant-client
- create/delete collection
- upsert points
- search top_k

## Вне scope

- quantization
- hybrid

## Результат (deliverables)

- adapters/vectordb_qdrant

## Критерии готовности

- интеграционный тест против compose Qdrant

## Зависит от

- [03. Docker Compose: только Qdrant](./03-compose-qdrant.md)
- [05. Конфиг приложения из env](./05-settings.md)

## Документация

- `ARCHITECTURE.md §8 VectorDB`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

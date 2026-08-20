# Этап 19. Embedding: один локальный моделью

**Slug:** `embedding-service`  
**Статус:** done

## Цель

Посчитать векторы для списка текстов.

## В scope

- sentence-transformers одна маленькая модель (зафиксировать имя)
- batch encode
- порт EmbeddingProvider

## Вне scope

- MRL truncate
- API providers
- кеш

## Результат (deliverables)

- packages/embedding + adapter local

## Критерии готовности

- encode 2 текстов → одинаковая dim, L2/cosine готов

## Зависит от

- [02. Python workspace и зависимости ядра](./02-python-workspace.md)

## Документация

- `DEPENDENCIES.md §4`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

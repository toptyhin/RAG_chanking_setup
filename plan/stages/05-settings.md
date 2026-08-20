# Этап 05. Конфиг приложения из env

**Slug:** `settings`  
**Статус:** done

## Цель

Единые настройки путей и URL.

## В scope

- pydantic-settings
- DATA_DIR, SQLITE_URL, QDRANT_URL
- пример .env.example

## Вне scope

- секреты провайдеров LLM

## Результат (deliverables)

- packages/domain или apps/api settings
- .env.example

## Критерии готовности

- приложение читает QDRANT_URL из env

## Зависит от

- [02. Python workspace и зависимости ядра](./02-python-workspace.md)

## Документация

- `ARCHITECTURE.md §8`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

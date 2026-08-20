# Этап 06. MetaDB: проекты

**Slug:** `metadb-projects`  
**Статус:** done

## Цель

SQLite + таблица projects.

## В scope

- SQLAlchemy models Project
- адаптер adapters/metadb_sqlite
- create_all / alembic init с одной ревизией

## Вне scope

- artifacts, runs

## Результат (deliverables)

- миграция
- CRUD на уровне репозитория

## Критерии готовности

- можно создать и прочитать project в SQLite файле

## Зависит от

- [04. Домен: типы артефактов и ID](./04-domain-artifacts.md)
- [05. Конфиг приложения из env](./05-settings.md)

## Документация

- `ARCHITECTURE.md §8 MetaDB`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

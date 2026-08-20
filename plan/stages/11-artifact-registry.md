# Этап 11. Artifact Registry API

**Slug:** `artifact-registry`  
**Статус:** done

## Цель

Список и получение артефактов проекта.

## В scope

- таблица/репозиторий artifacts
- GET list/filter by type
- parent_ids, content_hash

## Вне scope

- pipeline выполнения

## Результат (deliverables)

- API artifacts

## Критерии готовности

- uploaded raw_bundle виден в list

## Зависит от

- [10. Загрузка raw_bundle](./10-upload-raw-bundle.md)
- [06. MetaDB: проекты](./06-metadb-projects.md)

## Документация

- `ARCHITECTURE.md §5 Registry`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

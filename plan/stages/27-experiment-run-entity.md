# Этап 27. ExperimentRun в MetaDB

**Slug:** `experiment-run-entity`  
**Статус:** done

## Цель

Хранить run: mode, fixed, swept, status.

## В scope

- таблица experiment_runs + metrics_rows
- репозиторий create/update status

## Вне scope

- исполнение сетки

## Результат (deliverables)

- модели + миграция

## Критерии готовности

- можно создать run со status=pending

## Зависит от

- [06. MetaDB: проекты](./06-metadb-projects.md)
- [04. Домен: типы артефактов и ID](./04-domain-artifacts.md)

## Документация

- `ARCHITECTURE.md §9`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

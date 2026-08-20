# Этап 43. Фоновый Task Runner

**Slug:** `background-runner`  
**Статус:** done

## Цель

Не блокировать HTTP на долгих run.

## В scope

- in-process background
- status running/completed/failed
- ошибки в run.error

## Вне scope

- Celery

## Результат (deliverables)

- adapters/queue_local

## Критерии готовности

- POST возвращает run_id сразу; GET дожидается completed

## Зависит от

- [29. API: запуск и статус retrieval run](./29-api-start-retrieval-run.md)
- [27. ExperimentRun в MetaDB](./27-experiment-run-entity.md)

## Документация

- `ARCHITECTURE.md §6.3`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

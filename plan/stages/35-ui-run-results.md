# Этап 35. UI: запуск retrieval и таблица метрик

**Slug:** `ui-run-results`  
**Статус:** done

## Цель

Запустить run и показать результаты.

## В scope

- форма fixed/swept упрощённая
- poll GET status
- таблица metrics

## Вне scope

- Pareto charts
- SSE

## Результат (deliverables)

- страница experiment

## Критерии готовности

- пользователь видит Recall@k без curl

## Зависит от

- [34. UI: prep → chunk или BYO](./34-ui-prepare-chunks.md)
- [29. API: запуск и статус retrieval run](./29-api-start-retrieval-run.md)
- [30. Сетка swept (2 оси максимум)](./30-orchestrator-grid.md)

## Документация

- `ARCHITECTURE.md §13`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

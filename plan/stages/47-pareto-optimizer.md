# Этап 47. Pareto по результатам grid

**Slug:** `pareto-optimizer`  
**Статус:** done

## Цель

Построить парето-фронт.

## В scope

- оси recall, latency_p95, index_size
- список non-dominated
- API field pareto

## Вне scope

- авторекомендации Model Advisor

## Результат (deliverables)

- packages/optimize

## Критерии готовности

- на синтетических 5 точках фронт корректен

## Зависит от

- [30. Сетка swept (2 оси максимум)](./30-orchestrator-grid.md)
- [41. Метрики размера индекса](./41-index-size-metrics.md)

## Документация

- `ARCHITECTURE.md §7.9`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

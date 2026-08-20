# Этап 30. Сетка swept (2 оси максимум)

**Slug:** `orchestrator-grid`  
**Статус:** done

## Цель

Перебор небольшого grid.

## В scope

- cartesian product fixed×swept
- цикл по точкам
- metrics_row на точку

## Вне scope

- Pareto
- 3+ оси сразу

## Результат (deliverables)

- расширение orchestrator

## Критерии готовности

- 2 модели или 2 top_k → 2+ строки результатов

## Зависит от

- [28. Orchestrator: один retrieval-конфиг](./28-orchestrator-single-config.md)

## Документация

- `evaluation-axes.md принцип одной оси`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

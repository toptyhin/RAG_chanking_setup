# Этап 41. Метрики размера индекса

**Slug:** `index-size-metrics`  
**Статус:** done

## Цель

Снимать RAM/disk (или proxy) из Qdrant.

## В scope

- collection info / telemetry best-effort
- поля index_ram_mb / index_disk_mb

## Вне scope

- идеальная точность cgroup

## Результат (deliverables)

- ops metrics в results

## Критерии готовности

- в metrics_row есть size поля (или null + documented fallback)

## Зависит от

- [40. Quantization в Index](./40-index-quantization.md)

## Документация

- `ARCHITECTURE.md ops metrics`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

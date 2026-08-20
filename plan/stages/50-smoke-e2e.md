# Этап 50. Smoke E2E и README quickstart

**Slug:** `smoke-e2e`  
**Статус:** done

## Цель

Сквозной сценарий MVP и документация запуска.

## В scope

- скрипт/make smoke: upload→prep→chunk→testset→run→report
- rageval/README quickstart
- ссылка на plan

## Вне scope

- SaaS
- multimodal

## Результат (deliverables)

- scripts/smoke.sh или pytest e2e
- обновлённый README

## Критерии готовности

- на clean machine по README проходит happy path

## Зависит от

- [36. Compose: api + web + qdrant](./36-compose-full.md)
- [49. UI: Pareto и ссылка на отчёт](./49-ui-pareto-report.md)

## Документация

- `ARCHITECTURE.md MVP Must`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

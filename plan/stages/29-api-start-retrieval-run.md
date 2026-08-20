# Этап 29. API: запуск и статус retrieval run

**Slug:** `api-start-retrieval-run`  
**Статус:** done

## Цель

HTTP создать run и получить результат.

## В scope

- POST /experiments
- GET /experiments/{id}
- пока sync в запросе OK

## Вне scope

- SSE
- cancel

## Результат (deliverables)

- роуты experiments

## Критерии готовности

- e2e API: BYO chunks + testset → metrics в ответе/GET

## Зависит от

- [28. Orchestrator: один retrieval-конфиг](./28-orchestrator-single-config.md)
- [08. FastAPI skeleton + health](./08-fastapi-skeleton.md)

## Документация

- `ARCHITECTURE.md §13`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

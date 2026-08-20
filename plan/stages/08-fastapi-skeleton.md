# Этап 08. FastAPI skeleton + health

**Slug:** `fastapi-skeleton`  
**Статус:** done

## Цель

Запустить API и проверить живость.

## В scope

- apps/api main
- GET /health
- wiring settings + lifespan

## Вне scope

- бизнес-роуты

## Результат (deliverables)

- uvicorn стартует локально

## Критерии готовности

- curl /health → 200

## Зависит от

- [05. Конфиг приложения из env](./05-settings.md)
- [02. Python workspace и зависимости ядра](./02-python-workspace.md)

## Документация

- `ARCHITECTURE.md §3 Presentation/API`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 44. Прогресс run (SSE или polling)

**Slug:** `progress-sse`  
**Статус:** done

## Цель

Отдавать прогресс сетки.

## В scope

- percent + current config
- SSE endpoint или улучшенный poll payload

## Вне scope

- WebSocket обязательный

## Результат (deliverables)

- API progress

## Критерии готовности

- UI может показать «3/10 configs»

## Зависит от

- [43. Фоновый Task Runner](./43-background-runner.md)
- [35. UI: запуск retrieval и таблица метрик](./35-ui-run-results.md)

## Документация

- `ARCHITECTURE.md orchestrator progress`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 53. Запрет тихого hash-fallback эмбеддинга

**Slug:** `embedding-fallback-guard`
**Статус:** done
**Приоритет:** P0 (корректность метрик)

## Проблема

В `embedding_for_point` при `embedding.dimension > provider.dimension` создаётся
`HashEmbeddingProvider` (`eval_point.py:54-56`) — это детерминированные, но по сути
случайные векторы. В бенчмарке такая точка даёт правдоподобно выглядящие, но
бессмысленные метрики: пользователь думает, что сравнил «размерность 1024», а на
деле замерил хеш-эмбеддинг.

`EmbeddingService` уже запрещает `dimension > provider.dimension` (service.py:72-75),
но orchestrator обходит это, подменяя провайдер.

## Цель

Убрать молчаливый fallback на hash-провайдер в продакшн-пути оркестратора.
Некорректная точка сетки должна падать явной ошибкой (или помечаться как skipped
с причиной), а не тихо возвращать мусор.

## В scope

- `eval_point.py`: убрать создание `HashEmbeddingProvider` для `dim > provider.dimension`.
- Явная ошибка `ValueError` с понятным сообщением (модель, запрошенный dim, макс dim).
- Оркестратор: точка помечается `status="failed"`/`error` в строке метрик, grid
  продолжает остальные точки (не падает целиком).
- `HashEmbeddingProvider` остаётся только для тестов/фикстур (не в дефолтном пути).

## Вне scope

- Реальная поддержка dim выше нативной размерности (это не MRL — это апскейл).

## Результат (deliverables)

- Правка `packages/orchestrator/.../eval_point.py`.
- Тест: точка с `embedding.dimension` > нативной → явная ошибка/failed row,
  а не hash-вектора.

## Критерии готовности

- В отчёте невозможно получить метрики по hash-эмбеддингу через обычный запуск run.
- Ошибочная точка не роняет весь grid.

## Зависит от

- [42. MRL / truncate dimension](./42-mrl-dimension.md)
- [19. Embedding: один локальный моделью](./19-embedding-service.md)

## Документация

- `ARCHITECTURE.md §7.3`

## Оценка сложности

S.

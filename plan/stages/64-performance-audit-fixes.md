# Этап 64. Performance audit fixes

**Slug:** `performance-audit-fixes`  
**Статус:** done
**Приоритет:** P0–P2

## Цель

Устранить блокировку event loop и повторную тяжёлую работу в Lab-экспериментах:
переиспользовать prep/chunk/index/query/relevance артефакты, не строить dense index
для sparse-only точек и сократить стоимость I/O/телеметрии.

## В scope

- bounded local worker pool для синхронной CPU/I/O части job;
- группировка retrieval grid по build-конфигурации и reuse `index_run`;
- content-addressed clean/chunk artifacts и MRL native-cache;
- batched Qdrant upsert, query/relevance memoization, дешёвая size telemetry;
- SSE progress UI и сокращение SQLite writes;
- reuse default upload prep и ограниченный model preload.

## Критерии готовности

- sparse-only точка не вызывает embedding/Qdrant;
- search-only оси используют один collection/index build;
- MRL dimensions требуют один native encode;
- focused backend/frontend tests проходят.

## Зависит от

- [43. Фоновый Task Runner](./43-background-runner.md)
- [44. Прогресс run](./44-progress-sse.md)
- [51. Runtime model registry](./51-runtime-model-registry.md)
- [56. Кеш sparse BM25](./56-sparse-index-cache.md)

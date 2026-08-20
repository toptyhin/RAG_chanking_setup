# Этап 52. Rerank: глубина кандидатов (funnel top_n → keep)

**Slug:** `rerank-candidate-depth`
**Статус:** done
**Приоритет:** P0 (корректность метрик)

## Проблема

В `evaluate_retrieval_point` retrieval достаёт ровно `top_k` кандидатов, а реранк
потом просит `top_n = max(top_k*2, top_k)` (`eval_point.py:154`). Кандидатов
всего `top_k`, поэтому `rerank_retrieval` физически видит только `top_k` и лишь
переупорядочивает финальный список. Классический паттерн «достать 50 → реранкнуть
в 5» невозможен: глубина воронки схлопнута до итогового `top_k`.

Следствие: ось `rerank.enabled` меряет не эффект реранка, а перестановку уже
выбранного топа. Сравнение конфигов с реранком и без него — недостоверно.

## Цель

При включённом реранке retrieval должен доставать `candidate_k = max(top_k, rerank.top_n)`
кандидатов, реранк — переупорядочивать их и оставлять `keep` (по умолчанию `top_k`).
Метрики считаются по финальному списку длиной `keep`.

## В scope

- `eval_point.py`: вычислить `candidate_k` до retrieval, если `rerank.enabled`.
- Прокинуть `candidate_k` в `dense_retrieve` / `sparse_retrieve` / `hybrid_retrieve`
  (для hybrid — увеличить `candidate_k` перед RRF).
- `rerank.top_n` и `rerank.keep` — реальные, а не срезанные до `top_k`.
- Значения по умолчанию: `top_n=50`, `keep=top_k` (документировать).

## Вне scope

- LLM-rerank.
- Изменение самой cross-encoder модели.

## Результат (deliverables)

- Правка `packages/orchestrator/.../eval_point.py`.
- Тест: при `rerank.enabled=true, top_n=50, keep=5, top_k=10` в реранк уходит
  ≥ min(50, доступные) кандидатов, финальный список = 5.

## Критерии готовности

- На фикстуре с > `top_k` релевантными кандидатами реранк меняет Recall@k
  относительно чистого retrieval (а не только порядок первых `top_k`).
- Latency реранка растёт с ростом `top_n`.

## Зависит от

- [39. Rerank on/off](./39-rerank-cross-encoder.md)
- [28. Orchestrator: один retrieval-конфиг](./28-orchestrator-single-config.md)

## Документация

- `ARCHITECTURE.md §7.6`
- `evaluation-axes.md §2.2` (глубина top-N → top-k)

## Оценка сложности

S. Точечная правка воронки + тест.

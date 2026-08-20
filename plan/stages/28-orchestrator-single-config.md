# Этап 28. Orchestrator: один retrieval-конфиг

**Slug:** `orchestrator-single-config`  
**Статус:** done

## Цель

Синхронный прогон Retrieval Lab на 1 точке.

## В scope

- evaluates=retrieval
- chunk_set + test_set + embed/index/retrieve/eval
- запись metrics

## Вне scope

- grid swept
- фон
- prep/chunk lab

## Результат (deliverables)

- packages/orchestrator

## Критерии готовности

- API или service: один run → Recall/nDCG/latency в БД

## Зависит от

- [22. Index service без квантования](./22-index-service-basic.md)
- [23. Dense retrieval + latency](./23-dense-retrieve.md)
- [24. Метрика Recall@k](./24-metrics-recall.md)
- [25. Метрика nDCG@k](./25-metrics-ndcg.md)
- [27. ExperimentRun в MetaDB](./27-experiment-run-entity.md)
- [18. Импорт test_set](./18-testset-import.md)

## Документация

- `evaluation-flows.md Retrieval Lab`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

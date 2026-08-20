# Этап 24. Метрика Recall@k

**Slug:** `metrics-recall`  
**Статус:** done

## Цель

Считать Recall@k по разметке.

## В scope

- функция recall_at_k
- агрегат mean по queries
- unit-тесты

## Вне scope

- nDCG
- e2e metrics

## Результат (deliverables)

- packages/eval

## Критерии готовности

- на фикстуре известный Recall@1/5

## Зависит от

- [04. Домен: типы артефактов и ID](./04-domain-artifacts.md)

## Документация

- `evaluation-axes.md метрики`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

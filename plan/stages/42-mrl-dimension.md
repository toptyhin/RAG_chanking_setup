# Этап 42. MRL / truncate dimension

**Slug:** `mrl-dimension`  
**Статус:** done

## Цель

Усечь векторы до dim.

## В scope

- параметр dimension
- truncate перед index
- кеш ключ включает dim

## Вне scope

- обучение MRL

## Результат (deliverables)

- embedding service

## Критерии готовности

- две dim → разные коллекции, сравнимы в grid

## Зависит от

- [20. FS cache эмбеддингов](./20-embedding-cache.md)
- [30. Сетка swept (2 оси максимум)](./30-orchestrator-grid.md)

## Документация

- `evaluation-axes.md MRL`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

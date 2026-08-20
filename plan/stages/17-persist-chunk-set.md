# Этап 17. Сохранение chunk_set из reference

**Slug:** `persist-chunk-set`  
**Статус:** done

## Цель

Пройти clean → chunk → artifact.

## В scope

- API/service create chunk_set from clean + reference config
- snapshot chunk_pipeline в meta

## Вне scope

- несколько стратегий

## Результат (deliverables)

- artifact chunk_set

## Критерии готовности

- можно LIST chunk_set проекта

## Зависит от

- [15. Reference chunker (fixed size)](./15-chunk-reference.md)
- [14. Сохранение clean_corpus](./14-persist-clean-corpus.md)

## Документация

- `ARCHITECTURE.md §5`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

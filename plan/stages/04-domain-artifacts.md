# Этап 04. Домен: типы артефактов и ID

**Slug:** `domain-artifacts`  
**Статус:** done

## Цель

Описать сущности артефактов без I/O.

## В scope

- enum ArtifactType
- модели RawBundle/CleanCorpus/ChunkSet/TestSet/IndexRun/ExperimentRun (Pydantic)
- генерация id

## Вне scope

- сохранение в БД
- файлы на диске

## Результат (deliverables)

- packages/domain/...

## Критерии готовности

- модели валидируются unit-тестами на примерах JSON

## Зависит от

- [02. Python workspace и зависимости ядра](./02-python-workspace.md)

## Документация

- `ARCHITECTURE.md §5`
- `evaluation-flows.md §2`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

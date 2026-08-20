# Этап 14. Сохранение clean_corpus

**Slug:** `persist-clean-corpus`  
**Статус:** done

## Цель

Записать результат prep как артефакт.

## В scope

- сериализация документов
- ObjectStore + Registry
- API trigger prep → clean_corpus id

## Вне scope

- сравнение нескольких prep в Lab

## Результат (deliverables)

- endpoint или service run_prep

## Критерии готовности

- есть скачиваемый/читаемый clean_corpus artifact

## Зависит от

- [12. Prep: plaintext/markdown](./12-prep-plaintext.md)
- [11. Artifact Registry API](./11-artifact-registry.md)
- [07. ObjectStore: локальный FS](./07-object-store-fs.md)

## Документация

- `ARCHITECTURE.md §5`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

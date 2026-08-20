# Этап 15. Reference chunker (fixed size)

**Slug:** `chunk-reference`  
**Статус:** done

## Цель

Один простой chunker для Retrieval Lab.

## В scope

- size + overlap
- стабильные chunk_id
- привязка к doc_id

## Вне scope

- semantic chunking
- Chunk Lab sweep

## Результат (deliverables)

- packages/chunking reference

## Критерии готовности

- clean_corpus → chunk_set с N чанками

## Зависит от

- [14. Сохранение clean_corpus](./14-persist-clean-corpus.md)

## Документация

- `evaluation-flows.md reference chunker`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

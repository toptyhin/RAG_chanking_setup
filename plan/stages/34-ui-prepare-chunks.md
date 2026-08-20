# Этап 34. UI: prep → chunk или BYO

**Slug:** `ui-prepare-chunks`  
**Статус:** done

## Цель

Минимальные кнопки подготовки данных.

## В scope

- кнопка Run plaintext/PDF prep
- кнопка reference chunk
- import BYO JSON + test_set

## Вне scope

- Chunk Lab comparison
- полный cascade wizard

## Результат (deliverables)

- простые forms

## Критерии готовности

- из UI получается chunk_set + test_set

## Зависит от

- [33. UI: upload raw и просмотр артефактов](./33-ui-artifacts-upload.md)
- [14. Сохранение clean_corpus](./14-persist-clean-corpus.md)
- [17. Сохранение chunk_set из reference](./17-persist-chunk-set.md)
- [18. Импорт test_set](./18-testset-import.md)

## Документация

- `evaluation-flows.md каскад`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 18. Импорт test_set

**Slug:** `testset-import`  
**Статус:** done

## Цель

Загрузить вопросы и релевантность по chunk_id.

## В scope

- JSON schema query → relevant_chunk_ids
- регистрация test_set
- базовая валидация ссылок

## Вне scope

- LLM testgen
- span matching

## Результат (deliverables)

- POST test-sets/import

## Критерии готовности

- test_set доступен для run

## Зависит от

- 16 или 17
- [11. Artifact Registry API](./11-artifact-registry.md)

## Документация

- `evaluation-flows.md §7`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 16. Импорт BYO chunk_set

**Slug:** `byo-chunks-import`  
**Статус:** done

## Цель

Загрузка чужих чанков JSON.

## В scope

- схема import
- валидация id/text/doc_id
- регистрация chunk_set

## Вне scope

- оценка наших chunker’ов

## Результат (deliverables)

- POST import chunks

## Критерии готовности

- BYO JSON становится chunk_set в registry

## Зависит от

- [11. Artifact Registry API](./11-artifact-registry.md)
- [04. Домен: типы артефактов и ID](./04-domain-artifacts.md)

## Документация

- `evaluation-flows.md BYO`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

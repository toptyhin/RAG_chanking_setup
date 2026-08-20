# Этап 40. Quantization в Index

**Slug:** `index-quantization`  
**Статус:** done

## Цель

Создание коллекций с quant config.

## В scope

- none / binary (± rescore если поддерживается клиентом)
- передача в Qdrant
- ось в swept

## Вне scope

- все методы quant из ideas

## Результат (deliverables)

- index service + adapter

## Критерии готовности

- два index_run отличаются размером/конфигом

## Зависит от

- [22. Index service без квантования](./22-index-service-basic.md)
- [21. Адаптер Qdrant: CRUD коллекции](./21-qdrant-adapter.md)

## Документация

- `ideas.md quantization`
- `DEPENDENCIES Qdrant`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

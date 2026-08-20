# Этап 12. Prep: plaintext/markdown

**Slug:** `prep-plaintext`  
**Статус:** done

## Цель

Минимальный prep pipeline без PDF.

## В scope

- чтение .txt/.md из raw_bundle
- нормализация переносов
- выход clean_corpus в памяти/модели

## Вне scope

- OCR
- PDF
- dedup

## Результат (deliverables)

- packages/prep pipeline plaintext

## Критерии готовности

- из fixture raw → clean_corpus с doc_id и text

## Зависит от

- [04. Домен: типы артефактов и ID](./04-domain-artifacts.md)
- [10. Загрузка raw_bundle](./10-upload-raw-bundle.md)

## Документация

- `evaluation-flows.md Prep Lab`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

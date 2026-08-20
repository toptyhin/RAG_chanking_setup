# Этап 13. Prep: PDF extract

**Slug:** `prep-pdf`  
**Статус:** done

## Цель

Добавить извлечение текста из PDF.

## В scope

- pypdf или pymupdf на .pdf
- page в meta
- ошибки битых файлов в метриках prep

## Вне scope

- OCR сканов
- DOCX

## Результат (deliverables)

- расширение prep pipeline

## Критерии готовности

- PDF fixture даёт непустой текст

## Зависит от

- [12. Prep: plaintext/markdown](./12-prep-plaintext.md)

## Документация

- `DEPENDENCIES.md §5`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 07. ObjectStore: локальный FS

**Slug:** `object-store-fs`  
**Статус:** done

## Цель

Сохранять и читать бинарники/JSON по ключу.

## В scope

- put/get/exists/delete
- корень DATA_DIR/objects

## Вне scope

- S3
- дедуп контента

## Результат (deliverables)

- adapters/storage_fs

## Критерии готовности

- файл записан и прочитан обратно

## Зависит от

- [05. Конфиг приложения из env](./05-settings.md)

## Документация

- `ARCHITECTURE.md §8 ObjectStore`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

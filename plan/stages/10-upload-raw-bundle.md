# Этап 10. Загрузка raw_bundle

**Slug:** `upload-raw-bundle`  
**Статус:** done

## Цель

Принять файлы и зарегистрировать сырой корпус.

## В scope

- multipart upload одного или нескольких файлов
- сохранение в ObjectStore
- метаданные манифеста

## Вне scope

- parse PDF
- очистка

## Результат (deliverables)

- endpoint upload
- запись artifact meta

## Критерии готовности

- после upload есть artifact type=raw_bundle с файлами на диске

## Зависит от

- [07. ObjectStore: локальный FS](./07-object-store-fs.md)
- [09. API: CRUD projects](./09-api-projects.md)
- [04. Домен: типы артефактов и ID](./04-domain-artifacts.md)

## Документация

- `evaluation-flows.md raw_bundle`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 48. HTML отчёт

**Slug:** `html-report`  
**Статус:** done

## Цель

Сгенерировать отчёт по run.

## В scope

- Jinja2 шаблон
- таблица метрик + pareto
- сохранить в ObjectStore

## Вне scope

- PDF

## Результат (deliverables)

- packages/report
- download endpoint

## Критерии готовности

- есть HTML файл по run_id

## Зависит от

- [47. Pareto по результатам grid](./47-pareto-optimizer.md)
- [07. ObjectStore: локальный FS](./07-object-store-fs.md)

## Документация

- `DEPENDENCIES.md jinja2`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

# Этап 02. Python workspace и зависимости ядра

**Slug:** `python-workspace`  
**Статус:** done

## Цель

Подключить pyproject/uv или poetry для api + packages без ML.

## В scope

- pyproject.toml / workspace
- fastapi, uvicorn, pydantic, sqlalchemy — по DEPENDENCIES
- editable install packages

## Вне scope

- torch
- sentence-transformers
- Next.js

## Результат (deliverables)

- pyproject.toml
- минимальный requirements/lock
- скрипт установки в README

## Критерии готовности

- `pip install -e .` (или uv sync) проходит
- импорт packages.domain успешен

## Зависит от

- [01. Каркас каталогов rageval](./01-scaffold-tree.md)

## Документация

- `DEPENDENCIES.md §2`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

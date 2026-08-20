# Этап 03. Docker Compose: только Qdrant

**Slug:** `compose-qdrant`  
**Статус:** done

## Цель

Поднять векторную БД локально.

## В scope

- docker-compose.yml с qdrant:v1.18.2
- volume для storage
- порт 6333

## Вне scope

- api/web контейнеры
- сеть приложения

## Результат (deliverables)

- docker-compose.yml
- краткая инструкция up/down

## Критерии готовности

- `docker compose up -d qdrant` → health/ready отвечает

## Зависит от

- [01. Каркас каталогов rageval](./01-scaffold-tree.md)

## Документация

- `DEPENDENCIES.md §1`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

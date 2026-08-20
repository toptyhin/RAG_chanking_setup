# Этап 36. Compose: api + web + qdrant

**Slug:** `compose-full`  
**Статус:** done

## Цель

Собрать полный local stack.

## В scope

- Dockerfile api
- Dockerfile web
- сервисы в compose
- общий volume data

## Вне scope

- GPU image
- ollama

## Результат (deliverables)

- docker-compose.yml полный
- инструкция one-command up

## Критерии готовности

- stack поднимается, UI бьёт в API, Qdrant доступен

## Зависит от

- [03. Docker Compose: только Qdrant](./03-compose-qdrant.md)
- [08. FastAPI skeleton + health](./08-fastapi-skeleton.md)
- [31. Next.js scaffold apps/web](./31-nextjs-scaffold.md)

## Документация

- `ARCHITECTURE.md §12`

## Оценка сложности

S (маленький этап). Не расширять scope без отдельного этапа.

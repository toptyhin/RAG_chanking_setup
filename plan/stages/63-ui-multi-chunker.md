# Этап 63. UI multi-chunker в «У меня есть документы»

**Slug:** `ui-multi-chunker`  
**Статус:** done

## Цель

Заменить форму эталонного чанкера селектором библиотек и ленивыми настройками провайдера.

## В scope

- select: semchunk → chunklet → reference_fixed (в конце)
- lazy mount формы после выбора
- `listChunkers` / `createChunkSet` в api.ts
- i18n ru/en

## Вне scope

- Chunk Lab UI
- Isaacus

## Результат (deliverables)

- documents cascade использует unified chunk API

## Критерии готовности

- из UI можно создать chunk_set каждым доступным провайдером

## Зависит от

- [62. Library adapters](./62-chunker-library-adapters.md)

## Оценка сложности

M

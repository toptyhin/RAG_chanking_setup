# Этап 65. Product completion: канонический flow и недостающие Labs

**Slug:** `product-completion-flow`  
**Статус:** done (2026-07-24)

## Цель

Завершить единый пользовательский путь:
`Overview → Data → Test set → Labs → Run → Results/Compare`.

## В scope

- отдельные маршруты этапов вместо tabbed mega-page;
- реальные Prep / Chunk / Retrieval Lab через Experiment Orchestrator;
- неперсистентное превью чанков перед созданием `chunk_set`;
- provenance test set (`synthetic` / `manual` / `imported`, reviewed);
- сравнение 2+ прогонов с baseline delta и config diff;
- RU/EN copy и обязательный Chunk Lab disclaimer.

## Критерии готовности

- один Lab mode на run, артефакты остаются чекпоинтами;
- focused pytest проходит;
- `apps/web` build проходит;
- SSE страницы прогонов сохранён.

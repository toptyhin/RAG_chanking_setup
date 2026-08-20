# План реализации `rageval`

Код проекта создаётся в субдиректории [`rageval/`](../) репозитория `RAG`.  
Архитектура и правила: [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md), [`../../evaluation-flows.md`](../../evaluation-flows.md), [`../../DEPENDENCIES.md`](../../DEPENDENCIES.md).

## Прогресс

| Фаза | Статус |
|------|--------|
| A. Каркас (01–05) | **done** (2026-07-16) |
| B. Данные (06–11) | **done** (2026-07-16) |
| C. Prep/Chunk/Test (12–18) | **done** (2026-07-16) |
| D. Index/Retrieve/Eval (19–26) | **done** (2026-07-16) |
| E. Retrieval Lab API (27–30) | **done** (2026-07-16) |
| F. Retrieval modes (37–42) | see stage files |
| G. Compose UI (31–36) | **done** |
| H. Labs + отчёты (43–50) | **done** (2026-07-17) |
| I. Фиксы retrieval + закалка eval (52–60) | **done** (2026-07-21) |
| K. Performance audit (64) | **done** (2026-07-24) |
| L. Product completion flow (65) | **done** (2026-07-24) |

## Принципы плана

1. **Много маленьких этапов** — один этап = один проверяемый результат.
2. **Не смешивать Lab-режимы** раньше времени: сначала вертикаль Retrieval (BYO/reference), потом Prep/Chunk Lab.
3. **Сначала backend happy path без UI**, затем тонкий Next.js, затем усиление retrieval (hybrid/rerank/quant).
4. **Версии пакетов** брать из `DEPENDENCIES.md`.
5. Статус этапа менять в файле этапа: `pending` → `in_progress` → `done`.

## Порядок выполнения

| # | Этап | Файл |
|---|------|------|
| 01 | Каркас каталогов rageval | [`stages/01-scaffold-tree.md`](./stages/01-scaffold-tree.md) |
| 02 | Python workspace и зависимости ядра | [`stages/02-python-workspace.md`](./stages/02-python-workspace.md) |
| 03 | Docker Compose: только Qdrant | [`stages/03-compose-qdrant.md`](./stages/03-compose-qdrant.md) |
| 04 | Домен: типы артефактов и ID | [`stages/04-domain-artifacts.md`](./stages/04-domain-artifacts.md) |
| 05 | Конфиг приложения из env | [`stages/05-settings.md`](./stages/05-settings.md) |
| 06 | MetaDB: проекты | [`stages/06-metadb-projects.md`](./stages/06-metadb-projects.md) |
| 07 | ObjectStore: локальный FS | [`stages/07-object-store-fs.md`](./stages/07-object-store-fs.md) |
| 08 | FastAPI skeleton + health | [`stages/08-fastapi-skeleton.md`](./stages/08-fastapi-skeleton.md) |
| 09 | API: CRUD projects | [`stages/09-api-projects.md`](./stages/09-api-projects.md) |
| 10 | Загрузка raw_bundle | [`stages/10-upload-raw-bundle.md`](./stages/10-upload-raw-bundle.md) |
| 11 | Artifact Registry API | [`stages/11-artifact-registry.md`](./stages/11-artifact-registry.md) |
| 12 | Prep: plaintext/markdown | [`stages/12-prep-plaintext.md`](./stages/12-prep-plaintext.md) |
| 13 | Prep: PDF extract | [`stages/13-prep-pdf.md`](./stages/13-prep-pdf.md) |
| 14 | Сохранение clean_corpus | [`stages/14-persist-clean-corpus.md`](./stages/14-persist-clean-corpus.md) |
| 15 | Reference chunker (fixed size) | [`stages/15-chunk-reference.md`](./stages/15-chunk-reference.md) |
| 16 | Импорт BYO chunk_set | [`stages/16-byo-chunks-import.md`](./stages/16-byo-chunks-import.md) |
| 17 | Сохранение chunk_set из reference | [`stages/17-persist-chunk-set.md`](./stages/17-persist-chunk-set.md) |
| 18 | Импорт test_set | [`stages/18-testset-import.md`](./stages/18-testset-import.md) |
| 19 | Embedding: один локальный моделью | [`stages/19-embedding-service.md`](./stages/19-embedding-service.md) |
| 20 | FS cache эмбеддингов | [`stages/20-embedding-cache.md`](./stages/20-embedding-cache.md) |
| 21 | Адаптер Qdrant: CRUD коллекции | [`stages/21-qdrant-adapter.md`](./stages/21-qdrant-adapter.md) |
| 22 | Index service без квантования | [`stages/22-index-service-basic.md`](./stages/22-index-service-basic.md) |
| 23 | Dense retrieval + latency | [`stages/23-dense-retrieve.md`](./stages/23-dense-retrieve.md) |
| 24 | Метрика Recall@k | [`stages/24-metrics-recall.md`](./stages/24-metrics-recall.md) |
| 25 | Метрика nDCG@k | [`stages/25-metrics-ndcg.md`](./stages/25-metrics-ndcg.md) |
| 26 | Метрика MRR | [`stages/26-metrics-mrr.md`](./stages/26-metrics-mrr.md) |
| 27 | ExperimentRun в MetaDB | [`stages/27-experiment-run-entity.md`](./stages/27-experiment-run-entity.md) |
| 28 | Orchestrator: один retrieval-конфиг | [`stages/28-orchestrator-single-config.md`](./stages/28-orchestrator-single-config.md) |
| 29 | API: запуск и статус retrieval run | [`stages/29-api-start-retrieval-run.md`](./stages/29-api-start-retrieval-run.md) |
| 30 | Сетка swept (2 оси максимум) | [`stages/30-orchestrator-grid.md`](./stages/30-orchestrator-grid.md) |
| 31 | Next.js scaffold apps/web | [`stages/31-nextjs-scaffold.md`](./stages/31-nextjs-scaffold.md) |
| 32 | UI: список и создание проектов | [`stages/32-ui-projects.md`](./stages/32-ui-projects.md) |
| 33 | UI: upload raw и просмотр артефактов | [`stages/33-ui-artifacts-upload.md`](./stages/33-ui-artifacts-upload.md) |
| 34 | UI: prep → chunk или BYO | [`stages/34-ui-prepare-chunks.md`](./stages/34-ui-prepare-chunks.md) |
| 35 | UI: запуск retrieval и таблица метрик | [`stages/35-ui-run-results.md`](./stages/35-ui-run-results.md) |
| 36 | Compose: api + web + qdrant | [`stages/36-compose-full.md`](./stages/36-compose-full.md) |
| 37 | Sparse BM25 | [`stages/37-sparse-bm25.md`](./stages/37-sparse-bm25.md) |
| 38 | Hybrid RRF | [`stages/38-hybrid-rrf.md`](./stages/38-hybrid-rrf.md) |
| 39 | Rerank on/off | [`stages/39-rerank-cross-encoder.md`](./stages/39-rerank-cross-encoder.md) |
| 40 | Quantization в Index | [`stages/40-index-quantization.md`](./stages/40-index-quantization.md) |
| 41 | Метрики размера индекса | [`stages/41-index-size-metrics.md`](./stages/41-index-size-metrics.md) |
| 42 | MRL / truncate dimension | [`stages/42-mrl-dimension.md`](./stages/42-mrl-dimension.md) |
| 43 | Фоновый Task Runner | [`stages/43-background-runner.md`](./stages/43-background-runner.md) |
| 44 | Прогресс run (SSE или polling) | [`stages/44-progress-sse.md`](./stages/44-progress-sse.md) |
| 45 | Режим Prep Lab (минимум) | [`stages/45-prep-lab-mode.md`](./stages/45-prep-lab-mode.md) |
| 46 | Режим Chunk Lab (минимум) | [`stages/46-chunk-lab-mode.md`](./stages/46-chunk-lab-mode.md) |
| 47 | Pareto по результатам grid | [`stages/47-pareto-optimizer.md`](./stages/47-pareto-optimizer.md) |
| 48 | HTML отчёт | [`stages/48-html-report.md`](./stages/48-html-report.md) |
| 49 | UI: Pareto и ссылка на отчёт | [`stages/49-ui-pareto-report.md`](./stages/49-ui-pareto-report.md) |
| 50 | Smoke E2E и README quickstart | [`stages/50-smoke-e2e.md`](./stages/50-smoke-e2e.md) |
| 51 | Runtime model registry (HF + UI) | [`stages/51-runtime-model-registry.md`](./stages/51-runtime-model-registry.md) |
| 52 | Rerank: глубина кандидатов (funnel) | [`stages/52-rerank-candidate-depth.md`](./stages/52-rerank-candidate-depth.md) |
| 53 | Запрет тихого hash-fallback эмбеддинга | [`stages/53-embedding-fallback-guard.md`](./stages/53-embedding-fallback-guard.md) |
| 54 | Scalar (int8) quantization | [`stages/54-scalar-quantization.md`](./stages/54-scalar-quantization.md) |
| 55 | Ось HNSW-параметров | [`stages/55-hnsw-params-axis.md`](./stages/55-hnsw-params-axis.md) |
| 56 | Кеш sparse BM25 индекса | [`stages/56-sparse-index-cache.md`](./stages/56-sparse-index-cache.md) |
| 57 | Hybrid: взвешенное слияние + candidate_k | [`stages/57-hybrid-fusion-tuning.md`](./stages/57-hybrid-fusion-tuning.md) |
| 58 | Метрика answer-coverage | [`stages/58-answer-coverage-metric.md`](./stages/58-answer-coverage-metric.md) |
| 59 | Верификация разметки + graded relevance | [`stages/59-relevance-review-graded.md`](./stages/59-relevance-review-graded.md) |
| 60 | Закалка test_set (типы/no-answer/hard-neg) | [`stages/60-testset-hardening.md`](./stages/60-testset-hardening.md) |
| 61 | Chunker registry + unified options | [`stages/61-chunker-registry.md`](./stages/61-chunker-registry.md) |
| 62 | Library adapters + chunk API | [`stages/62-chunker-library-adapters.md`](./stages/62-chunker-library-adapters.md) |
| 63 | UI multi-chunker (documents) | [`stages/63-ui-multi-chunker.md`](./stages/63-ui-multi-chunker.md) |
| 64 | Performance audit fixes | [`stages/64-performance-audit-fixes.md`](./stages/64-performance-audit-fixes.md) |
| 65 | Product completion: canonical flow + Labs | [`stages/65-product-completion-flow.md`](./stages/65-product-completion-flow.md) |

## Фазы (группировка)

| Фаза | Этапы | Смысл |
|------|-------|--------|
| A. Каркас | 01–05 | дерево, python, compose qdrant, domain, settings |
| B. Данные | 06–11 | MetaDB, FS store, API, upload, registry |
| C. Prep/Chunk/Test | 12–18 | plaintext/PDF prep, chunk, BYO, test_set |
| D. Index/Retrieve/Eval | 19–26 | embed, cache, qdrant, dense, метрики, run entity |
| E. Retrieval Lab API | 27–30 | orchestrator, API, grid |
| F. UI + Compose | 31–36 | Next.js, экраны, полный docker compose |
| G. Retrieval усиление | 37–42 | sparse, hybrid, rerank, quant, size, MRL |
| H. Labs + отчёты | 43–50 | background, SSE, Prep/Chunk Lab, Pareto, report, smoke |
| I. Фиксы + закалка eval | 52–60 | funnel реранка, guard эмбеддинга, scalar quant, HNSW, кеш sparse, hybrid fusion, answer-coverage, graded/verified разметка, типы запросов |
| J. Multi-chunker | 61–63 | registry, semchunk/chunklet/reference adapters, UI documents |
| K. Performance audit | 64 | worker pool, artifact/index reuse, batched I/O, SSE |
| L. Product completion | 65 | canonical routes, Prep/Chunk UI, preview, provenance, run comparison |

### Фаза I — порядок и приоритеты

Продолжает нумерацию (51 — последний прежний этап). Правило прежнее: один этап =
один проверяемый результат, менять статус в файле этапа.

| Приоритет | Этапы | Смысл |
|-----------|-------|--------|
| P0 (корректность) | 52, 53 | текущие метрики врут: сломанная воронка реранка и тихий hash-fallback |
| P1 (полнота осей / стоимость) | 54, 55, 56 | scalar quant, HNSW-ось, кеш sparse-индекса |
| P2 (методология eval) | 57, 58, 59, 60 | hybrid fusion, answer-coverage, verified/graded разметка, типы запросов |

Рекомендуемый порядок внедрения: 52 → 53 → 54 → 55 → 56 → 57 → 58 → 59 → 60.
P0 закрывают достоверность сравнения по одному вопросу; P1 расширяют оси Pareto;
P2 переводят оценку с «одного вопроса» на стабильный golden core.

## MVP-готово после

Этап **50** (smoke + quickstart), при этом обязательный минимум продукта уже работает после **36** (полный compose + UI run/results). Этапы 37–49 усиливают качество и режимы Lab.

## Вне плана (later)

- SaaS адаптеры, Celery, auth
- Multimodal / video
- LLM testgen, e2e faithfulness, Model Advisor
- Query rewrite / HyDE

См. `ARCHITECTURE.md` §16 Later.

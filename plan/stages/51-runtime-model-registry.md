# Этап 51. Runtime embedding/rerank model registry

**Slug:** `runtime-model-registry`  
**Статус:** done

## Цель

Выбирать и загружать embedding/rerank модели в рантайме через HF Hub proxy и UI.

## В scope

- `adapters/hf_hub` поиск моделей (httpx)
- `ModelRegistry` + load jobs + SSE progress
- API `/models/*`; wire index/retrieve/experiments
- оси `embedding.model`, `rerank.model` (+ CrossEncoder)
- UI ModelPicker на New Run

## Вне scope

- GPU compose image
- Persist favorites в MetaDB

## Результат (deliverables)

- registry + HF catalog + web picker

## Критерии готовности

- search/load hash path без ML; ST/CE load с `[ml]`
- retrieve использует `IndexRun.embedding_model`

## Зависит от

- [19. Embedding](./19-embedding-service.md)
- [39. Rerank](./39-rerank-cross-encoder.md)
- [44. Progress SSE](./44-progress-sse.md)

## Документация

- `ARCHITECTURE.md` §8
- `DEPENDENCIES.md` (huggingface-hub в ml extra)

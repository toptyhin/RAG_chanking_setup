"""FastAPI entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rageval_api.embedding_factory import build_embedding_service
from rageval_api.model_registry import build_registry
from rageval_api.routes import (
    artifacts,
    chunking,
    content,
    embedding,
    experiments,
    health,
    indexing,
    llm,
    models,
    prep,
    projects,
    prompts,
    retrieve,
    testsets,
)
from rageval_domain.settings import get_settings
from rageval_embedding_providers import EmbeddingConfigStore
from rageval_llm_providers import LlmConfigStore, PromptStore
from rageval_llm_providers.rerank import RerankConfigStore
from rageval_metadb_sqlite import create_engine, create_session_factory, init_db
from rageval_queue_local import LocalTaskRunner
from rageval_storage_fs import FileSystemObjectStore
from rageval_vectordb_qdrant import QdrantVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.hf_token:
        # huggingface_hub / transformers read these env vars for auth + rate limits
        os.environ.setdefault("HF_TOKEN", settings.hf_token)
        os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", settings.hf_token)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.objects_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

    # Ensure SQLite parent directory exists for file URLs like ./data/rageval.db
    if settings.sqlite_url.startswith("sqlite"):
        # sqlite+aiosqlite:///./data/rageval.db → ./data/rageval.db
        raw = settings.sqlite_url.split("///", 1)[-1]
        db_path = Path(raw)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(settings.sqlite_url)
    await init_db(engine)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.object_store = FileSystemObjectStore(settings.objects_dir)
    app.state.embedding_service = build_embedding_service(settings)
    app.state.llm_config_store = LlmConfigStore(settings.data_dir / "llm_config.json")
    app.state.embedding_config_store = EmbeddingConfigStore(
        settings.data_dir / "embedding_config.json"
    )
    app.state.rerank_config_store = RerankConfigStore(
        settings.data_dir / "rerank_config.json"
    )
    app.state.model_registry = build_registry(
        cache_dir=settings.cache_dir,
        default_embedding=app.state.embedding_service,
        embedding_model=settings.embedding_model,
        rerank_model=settings.rerank_model,
        hf_token=settings.hf_token,
        embedding_config_loader=app.state.embedding_config_store.load,
        rerank_config_loader=app.state.rerank_config_store.load_or_none,
        llm_config_loader=app.state.llm_config_store.load,
    )
    # Restore the reranker selection across API restarts (model id used to be
    # in-memory only; the provider+model now live in rerank_config.json).
    rerank_config = app.state.rerank_config_store.load_or_none()
    if rerank_config is not None and rerank_config.model.strip():
        app.state.model_registry.set_current_rerank_model(rerank_config.model)
    app.state.qdrant = QdrantVectorStore(settings.qdrant_url)
    app.state.task_runner = LocalTaskRunner()
    app.state.prompt_store = PromptStore(settings.data_dir / "prompts.json")
    yield
    await app.state.task_runner.shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="rageval API", version="0.1.0", lifespan=lifespan)
    # Local MVP: browser UI (Next.js) calls API directly via NEXT_PUBLIC_API_URL.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(artifacts.router)
    app.include_router(content.router)
    app.include_router(prep.router)
    app.include_router(chunking.router)
    app.include_router(testsets.router)
    app.include_router(indexing.router)
    app.include_router(retrieve.router)
    app.include_router(models.router)
    app.include_router(llm.router)
    app.include_router(embedding.router)
    app.include_router(prompts.router)
    app.include_router(experiments.router)
    return app


app = create_app()

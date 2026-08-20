"""Remote model catalog parsing / purpose filters."""

from __future__ import annotations

from rageval_llm_providers.catalog import (
    ModelPurpose,
    filter_gigachat_models,
    filter_openrouter_models,
    parse_gigachat_model,
    parse_openrouter_model,
)


def test_parse_openrouter_model_extracts_fields() -> None:
    info = parse_openrouter_model(
        {
            "id": "openai/gpt-4o-mini",
            "name": "GPT-4o Mini",
            "context_length": 128000,
            "architecture": {
                "modality": "text->text",
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
            "supported_parameters": [
                "temperature",
                "structured_outputs",
                "response_format",
                "tools",
                "structured_outputs",
            ],
        }
    )
    assert info is not None
    assert info.id == "openai/gpt-4o-mini"
    assert info.name == "GPT-4o Mini"
    assert info.context_length == 128000
    assert info.modality == "text->text"
    assert info.output_modalities == ["text"]
    assert info.supported_parameters == [
        "temperature",
        "structured_outputs",
        "response_format",
        "tools",
    ]
    assert info.dimension is None
    assert info.dimensions == []


def test_parse_openrouter_embedding_dims_from_known_and_description() -> None:
    mrl = parse_openrouter_model(
        {
            "id": "openai/text-embedding-3-small",
            "name": "Text Embedding 3 Small",
            "architecture": {
                "output_modalities": ["embeddings"],
                "input_modalities": ["text"],
            },
        }
    )
    assert mrl is not None
    assert mrl.dimension == 1536
    assert mrl.dimensions == [512, 1536]

    from_desc = parse_openrouter_model(
        {
            "id": "vendor/custom-embed",
            "name": "Custom",
            "description": (
                "encodes English sentences into a 768-dimensional dense vector space"
            ),
            "architecture": {
                "output_modalities": ["embeddings"],
                "input_modalities": ["text"],
            },
        }
    )
    assert from_desc is not None
    assert from_desc.dimension == 768
    assert from_desc.dimensions == []


def test_parse_openrouter_model_without_supported_parameters() -> None:
    info = parse_openrouter_model(
        {
            "id": "vendor/model",
            "name": "Model",
            "architecture": {"output_modalities": ["text"]},
        }
    )
    assert info is not None
    assert info.supported_parameters == []


def test_filter_openrouter_by_purpose() -> None:
    text = parse_openrouter_model(
        {
            "id": "a/chat",
            "name": "Chat",
            "context_length": 8_000,
            "architecture": {"output_modalities": ["text"], "input_modalities": ["text"]},
        }
    )
    emb = parse_openrouter_model(
        {
            "id": "a/embed",
            "name": "Embed",
            "context_length": 8_000,
            "architecture": {
                "output_modalities": ["embeddings"],
                "input_modalities": ["text"],
            },
        }
    )
    assert text and emb
    items = [text, emb]
    assert [m.id for m in filter_openrouter_models(items, purpose=ModelPurpose.text)] == [
        "a/chat"
    ]
    assert [
        m.id for m in filter_openrouter_models(items, purpose=ModelPurpose.embeddings)
    ] == ["a/embed"]


def test_filter_gigachat_by_purpose() -> None:
    chat = parse_gigachat_model({"id": "GigaChat-2-Max"})
    emb = parse_gigachat_model({"id": "Embeddings-2"})
    assert chat and emb
    assert chat.modality == "text→text"
    assert emb.modality == "text→embeddings"
    assert emb.context_length == 4_096
    assert emb.dimension == 1024
    items = [chat, emb]
    assert [m.id for m in filter_gigachat_models(items, purpose=ModelPurpose.text)] == [
        "GigaChat-2-Max"
    ]
    assert [
        m.id for m in filter_gigachat_models(items, purpose=ModelPurpose.embeddings)
    ] == ["Embeddings-2"]


def test_ollama_model_infos_merges_probe_and_known_mrl() -> None:
    from rageval_llm_providers.catalog import ollama_model_infos

    rows = ollama_model_infos(
        ["nomic-embed-text:latest", "unknown-embed"],
        dimensions_by_id={"unknown-embed": 512},
    )
    by_id = {r.id: r for r in rows}
    assert by_id["nomic-embed-text:latest"].dimension == 768
    assert by_id["nomic-embed-text:latest"].dimensions == [64, 128, 256, 512, 768]
    assert by_id["unknown-embed"].dimension == 512
    assert by_id["unknown-embed"].dimensions == []


def test_embedding_length_from_ollama_show() -> None:
    from rageval_llm_providers.limits import embedding_length_from_ollama_show

    dim, src = embedding_length_from_ollama_show(
        {"model_info": {"bert.embedding_length": 768, "bert.context_length": 2048}}
    )
    assert dim == 768
    assert src == "model_info.bert.embedding_length"

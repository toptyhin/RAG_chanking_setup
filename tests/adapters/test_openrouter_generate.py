"""OpenRouter generate sends structured outputs via response_format."""

from __future__ import annotations

import json
from typing import Any

import pytest

from rageval_llm_providers.catalog import RemoteModelInfo
from rageval_llm_providers.config import OpenRouterSettings
from rageval_llm_providers.openrouter import (
    OpenRouterProvider,
    apply_openrouter_structured_output,
    build_openrouter_response_format,
)
from rageval_llm_providers.question_prep import QUESTION_PREP_JSON_SCHEMA


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    @property
    def is_success(self) -> bool:
        return self.status_code < 400

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    last_json: dict[str, Any] | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> _FakeResponse:
        del headers
        assert url.endswith("/chat/completions")
        _FakeClient.last_json = json
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"questions":[{"level":"L1","question":"Q?",'
                                '"expected_answer":"A","source_quote":"quote",'
                                '"evidence_quotes":["quote"]}]}'
                            )
                        }
                    }
                ]
            }
        )


def test_build_openrouter_response_format_wraps_schema() -> None:
    wrapped = build_openrouter_response_format(
        {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
        name="demo",
    )
    assert wrapped["type"] == "json_schema"
    assert wrapped["json_schema"]["name"] == "demo"
    assert wrapped["json_schema"]["strict"] is True
    assert wrapped["json_schema"]["schema"]["additionalProperties"] is False


def test_apply_structured_outputs_uses_json_schema() -> None:
    body: dict[str, Any] = {"model": "x", "messages": []}
    apply_openrouter_structured_output(
        body,
        QUESTION_PREP_JSON_SCHEMA,
        supported_parameters=["structured_outputs", "response_format"],
    )
    assert body["response_format"]["type"] == "json_schema"
    assert body["provider"] == {"require_parameters": True}
    assert body["plugins"] == [{"id": "response-healing"}]


def test_apply_response_format_only_uses_json_object() -> None:
    """Gemma free: response_format without structured_outputs → json_object."""
    body: dict[str, Any] = {"model": "x", "messages": []}
    apply_openrouter_structured_output(
        body,
        QUESTION_PREP_JSON_SCHEMA,
        supported_parameters=["response_format", "temperature"],
    )
    assert body["response_format"] == {"type": "json_object"}
    assert body["provider"] == {"require_parameters": True}
    assert body["plugins"] == [{"id": "response-healing"}]


def test_apply_no_caps_skips_response_format() -> None:
    body: dict[str, Any] = {"model": "x", "messages": []}
    apply_openrouter_structured_output(
        body,
        QUESTION_PREP_JSON_SCHEMA,
        supported_parameters=["temperature"],
    )
    assert "response_format" not in body
    assert "provider" not in body
    assert "plugins" not in body


def test_openrouter_generate_sends_strict_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("rageval_llm_providers.openrouter.httpx.Client", _FakeClient)
    provider = OpenRouterProvider(
        OpenRouterSettings(
            api_key="test-key",
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
        )
    )
    monkeypatch.setattr(
        provider,
        "_supported_parameters_for",
        lambda _model: ["structured_outputs", "response_format"],
    )
    text = provider.generate("prompt", response_format=QUESTION_PREP_JSON_SCHEMA)
    assert "questions" in text
    assert _FakeClient.last_json is not None
    body = _FakeClient.last_json
    assert body["provider"] == {"require_parameters": True}
    assert body["plugins"] == [{"id": "response-healing"}]
    fmt = body["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["name"] == "rag_question_prep"
    schema = fmt["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["questions"]["items"]["additionalProperties"] is False
    assert schema["required"] == ["questions"]


def test_openrouter_generate_gemma_like_falls_back_to_json_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("rageval_llm_providers.openrouter.httpx.Client", _FakeClient)
    provider = OpenRouterProvider(
        OpenRouterSettings(
            api_key="test-key",
            model="google/gemma-4-31b-it:free",
        )
    )
    monkeypatch.setattr(
        provider,
        "list_model_infos",
        lambda *, purpose=None: [
            RemoteModelInfo(
                id="google/gemma-4-31b-it:free",
                name="Gemma",
                supported_parameters=["response_format", "temperature"],
            )
        ],
    )
    provider.generate("prompt", response_format=QUESTION_PREP_JSON_SCHEMA)
    assert _FakeClient.last_json is not None
    assert _FakeClient.last_json["response_format"] == {"type": "json_object"}
    assert _FakeClient.last_json["provider"] == {"require_parameters": True}


def test_openrouter_generate_omits_response_format_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("rageval_llm_providers.openrouter.httpx.Client", _FakeClient)
    provider = OpenRouterProvider(
        OpenRouterSettings(api_key="test-key", model="openai/gpt-4o")
    )
    provider.generate("prompt")
    assert _FakeClient.last_json is not None
    assert "response_format" not in _FakeClient.last_json
    assert "provider" not in _FakeClient.last_json

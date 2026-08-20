"""Ollama generate passes JSON schema via format."""

from __future__ import annotations

import json
from typing import Any

import pytest

from rageval_llm_providers.config import OllamaSettings
from rageval_llm_providers.ollama import OllamaProvider
from rageval_llm_providers.question_prep import QUESTION_PREP_JSON_SCHEMA


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

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

    def post(self, url: str, json: dict[str, Any] | None = None) -> _FakeResponse:
        assert url.endswith("/api/chat")
        _FakeClient.last_json = json
        return _FakeResponse(
            {
                "message": {
                    "content": (
                        '{"questions":[{"level":"L1","question":"Q?",'
                        '"expected_answer":"A","source_quote":"quote",'
                        '"evidence_quotes":["quote"]}]}'
                    )
                },
                "done_reason": "stop",
            }
        )


def test_ollama_generate_sends_format_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rageval_llm_providers.ollama.httpx.Client", _FakeClient)
    provider = OllamaProvider(
        OllamaSettings(base_url="http://ollama.test", model="qwen3.5:9b")
    )
    text = provider.generate("prompt", response_format=QUESTION_PREP_JSON_SCHEMA)
    assert "questions" in text
    assert _FakeClient.last_json is not None
    assert _FakeClient.last_json["format"] == QUESTION_PREP_JSON_SCHEMA
    assert _FakeClient.last_json["options"]["temperature"] == 0
    assert _FakeClient.last_json["options"]["num_predict"] == -1
    assert _FakeClient.last_json["think"] is False


def test_ollama_generate_omits_format_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rageval_llm_providers.ollama.httpx.Client", _FakeClient)
    provider = OllamaProvider(
        OllamaSettings(base_url="http://ollama.test", model="qwen3.5:9b")
    )
    provider.generate("prompt")
    assert _FakeClient.last_json is not None
    assert "format" not in _FakeClient.last_json
    assert "temperature" not in _FakeClient.last_json["options"]
    assert _FakeClient.last_json["options"]["num_predict"] == 8192


def test_ollama_generate_raises_on_length_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _TruncClient(_FakeClient):
        def post(self, url: str, json: dict[str, Any] | None = None) -> _FakeResponse:
            _FakeClient.last_json = json
            return _FakeResponse(
                {
                    "message": {"content": '{"questions":[{"level":"L1"}'},
                    "done_reason": "length",
                    "prompt_eval_count": 1000,
                    "eval_count": 4096,
                }
            )

    monkeypatch.setattr("rageval_llm_providers.ollama.httpx.Client", _TruncClient)
    provider = OllamaProvider(
        OllamaSettings(base_url="http://ollama.test", model="gemma4:latest")
    )
    with pytest.raises(RuntimeError, match="truncated"):
        provider.generate("prompt", response_format=QUESTION_PREP_JSON_SCHEMA)
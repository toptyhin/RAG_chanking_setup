"""Port for text LLM providers used by testgen / question prep."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from rageval_llm_providers.limits import ModelLimits


@dataclass(slots=True)
class ConnectionTestResult:
    ok: bool
    latency_ms: float
    message: str
    model: str | None = None
    models: list[str] | None = None


class LlmProvider(Protocol):
    def list_models(self) -> list[str]: ...

    def ping(self) -> ConnectionTestResult:
        """Cheap connectivity check (list models or tiny completion)."""
        ...

    def generate(
        self,
        prompt: str,
        *,
        response_format: dict[str, Any] | str | None = None,
    ) -> str:
        """Run a single-turn completion; returns assistant text.

        ``response_format`` is a JSON Schema object (or ``\"json\"``) when the
        backend supports constrained decoding. Ollama uses it as ``format``;
        OpenRouter wraps it as ``response_format.type=json_schema`` with
        ``strict=true``. Providers that do not support it ignore the argument.
        """
        ...

    def get_model_limits(self) -> ModelLimits:
        """Return context window for the configured model when known."""
        ...

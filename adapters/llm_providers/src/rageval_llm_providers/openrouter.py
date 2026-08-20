"""OpenRouter (OpenAI-compatible) HTTP client."""

from __future__ import annotations

import copy
import logging
import time
from typing import Any

import httpx

from rageval_llm_providers.catalog import (
    ModelPurpose,
    RemoteModelInfo,
    filter_openrouter_models,
    openrouter_output_modality_param,
    parse_openrouter_model,
)
from rageval_llm_providers.config import OpenRouterSettings
from rageval_llm_providers.limits import ModelLimits
from rageval_llm_providers.protocol import ConnectionTestResult

logger = logging.getLogger(__name__)


def _with_additional_properties_false(node: Any) -> Any:
    """Deep-copy a JSON Schema, setting ``additionalProperties: false`` on objects.

    OpenRouter/OpenAI ``strict: true`` structured outputs require this on every
    object schema node.
    """
    if not isinstance(node, dict):
        return node
    out = copy.deepcopy(node)
    is_object = out.get("type") == "object" or "properties" in out
    if is_object:
        out.setdefault("additionalProperties", False)
    props = out.get("properties")
    if isinstance(props, dict):
        out["properties"] = {
            key: _with_additional_properties_false(value) for key, value in props.items()
        }
    items = out.get("items")
    if isinstance(items, dict):
        out["items"] = _with_additional_properties_false(items)
    elif isinstance(items, list):
        out["items"] = [_with_additional_properties_false(item) for item in items]
    for key in ("$defs", "definitions"):
        defs = out.get(key)
        if isinstance(defs, dict):
            out[key] = {
                name: _with_additional_properties_false(value)
                for name, value in defs.items()
            }
    for key in ("anyOf", "oneOf", "allOf"):
        variants = out.get(key)
        if isinstance(variants, list):
            out[key] = [_with_additional_properties_false(item) for item in variants]
    return out


def build_openrouter_response_format(
    response_format: dict[str, Any] | str,
    *,
    name: str = "rageval_response",
    strict: bool = True,
) -> dict[str, Any]:
    """Wrap a plain JSON Schema into OpenRouter ``response_format``.

    See https://openrouter.ai/docs/guides/features/structured-outputs
    """
    if isinstance(response_format, str):
        if response_format.strip().lower() in {"json", "json_object"}:
            return {"type": "json_object"}
        raise ValueError(
            f"unsupported OpenRouter response_format string: {response_format!r}"
        )

    fmt_type = response_format.get("type")
    if fmt_type == "json_object":
        return {"type": "json_object"}
    if fmt_type == "json_schema" and isinstance(response_format.get("json_schema"), dict):
        # Already OpenAI/OpenRouter shaped; ensure strict when requested.
        wrapped = copy.deepcopy(response_format)
        js = wrapped["json_schema"]
        if strict:
            js["strict"] = True
            schema = js.get("schema")
            if isinstance(schema, dict):
                js["schema"] = _with_additional_properties_false(schema)
        js.setdefault("name", name)
        return wrapped

    schema = (
        _with_additional_properties_false(response_format)
        if strict
        else copy.deepcopy(response_format)
    )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": strict,
            "schema": schema,
        },
    }


def apply_openrouter_structured_output(
    body: dict[str, Any],
    response_format: dict[str, Any] | str,
    *,
    supported_parameters: list[str] | set[str] | tuple[str, ...] | None,
    name: str = "rag_question_prep",
) -> None:
    """Mutate ``body`` with the strongest response_format the model can honor.

    OpenRouter distinguishes:
    - ``structured_outputs`` → ``json_schema`` (strict schema)
    - ``response_format`` only → ``json_object`` (valid JSON, not schema-bound)

    Sending ``json_schema`` with ``provider.require_parameters`` to a model that
    only lists ``response_format`` yields HTTP 404 ("No endpoints found...").
    """
    caps = {str(p).strip() for p in (supported_parameters or []) if str(p).strip()}
    # Free / weaker endpoints often emit almost-JSON; heal when possible.
    # https://openrouter.ai/docs/guides/features/plugins/response-healing
    healing = [{"id": "response-healing"}]

    if "structured_outputs" in caps:
        body["response_format"] = build_openrouter_response_format(
            response_format,
            name=name,
            strict=True,
        )
        body["provider"] = {"require_parameters": True}
        body["plugins"] = healing
        return

    if "response_format" in caps:
        body["response_format"] = {"type": "json_object"}
        body["provider"] = {"require_parameters": True}
        body["plugins"] = healing
        logger.info(
            "OpenRouter model lacks structured_outputs; using json_object "
            "(supported_parameters=%s)",
            sorted(caps),
        )
        return

    logger.warning(
        "OpenRouter model advertises neither structured_outputs nor "
        "response_format; skipping constrained decoding (supported_parameters=%s)",
        sorted(caps),
    )


def _http_error_detail(response: httpx.Response) -> str:
    """Prefer OpenRouter JSON ``error.message`` over bare status text."""
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        text = (response.text or "").strip()
        return text or f"HTTP {response.status_code}"
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
        if isinstance(err, str) and err.strip():
            return err.strip()
        msg = payload.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    text = (response.text or "").strip()
    return text or f"HTTP {response.status_code}"


def _http_error_body(response: httpx.Response) -> str:
    text = (response.text or "").strip()
    if not text:
        return "(empty body)"
    if len(text) > 4000:
        return f"{text[:4000]}\n…({len(text)} chars total)"
    return text


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = _http_error_detail(response)
    body = _http_error_body(response)
    logger.error(
        "OpenRouter HTTP %s: %s\n--- response body ---\n%s\n--- end response body ---",
        response.status_code,
        detail,
        body,
    )
    raise httpx.HTTPStatusError(
        f"HTTP {response.status_code}: {detail}",
        request=response.request,
        response=response,
    )


class OpenRouterProvider:
    def __init__(self, settings: OpenRouterSettings, *, timeout: float = 20.0) -> None:
        self.settings = settings
        self.timeout = timeout
        self.generate_timeout = max(timeout, 180.0)

    @property
    def _base(self) -> str:
        return self.settings.base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key.strip()
        if not key:
            raise ValueError("OpenRouter API key is not configured")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://rageval.local",
            "X-Title": "rageval",
        }

    def list_model_infos(
        self, *, purpose: ModelPurpose = ModelPurpose.text
    ) -> list[RemoteModelInfo]:
        params = {"output_modalities": openrouter_output_modality_param(purpose)}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self._base}/models",
                headers=self._headers(),
                params=params,
            )
            _raise_for_status(response)
            payload = response.json()
        data = payload.get("data") or []
        items: list[RemoteModelInfo] = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            parsed = parse_openrouter_model(raw)
            if parsed is not None:
                items.append(parsed)
        return filter_openrouter_models(items, purpose=purpose)

    def list_models(self) -> list[str]:
        return [m.id for m in self.list_model_infos(purpose=ModelPurpose.text)]

    def _supported_parameters_for(self, model: str) -> list[str]:
        """Best-effort caps from OpenRouter /models; empty if lookup fails."""
        try:
            infos = self.list_model_infos(purpose=ModelPurpose.text)
        except Exception:  # noqa: BLE001
            logger.warning(
                "OpenRouter model catalog lookup failed for %s; "
                "structured output mode may be suboptimal",
                model,
                exc_info=True,
            )
            return []
        for item in infos:
            if item.id == model:
                return list(item.supported_parameters)
        # Some free variants only appear under output_modalities=all.
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self._base}/models",
                    headers=self._headers(),
                    params={"output_modalities": "all"},
                )
                _raise_for_status(response)
                payload = response.json()
        except Exception:  # noqa: BLE001
            return []
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return []
        for raw in data:
            if not isinstance(raw, dict) or raw.get("id") != model:
                continue
            parsed = parse_openrouter_model(raw)
            if parsed is not None:
                return list(parsed.supported_parameters)
        return []

    def generate(
        self,
        prompt: str,
        *,
        response_format: dict[str, Any] | str | None = None,
    ) -> str:
        model = self.settings.model.strip()
        if not model:
            raise ValueError("OpenRouter model is not configured")
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if response_format is not None:
            apply_openrouter_structured_output(
                body,
                response_format,
                supported_parameters=self._supported_parameters_for(model),
                name="rag_question_prep",
            )
        try:
            with httpx.Client(timeout=self.generate_timeout) as client:
                response = client.post(
                    f"{self._base}/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
                _raise_for_status(response)
                payload = response.json()
        except Exception:
            logger.error(
                "OpenRouter generate failed model=%s response_format=%s provider=%s",
                model,
                body.get("response_format"),
                body.get("provider"),
            )
            raise
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenRouter response missing choices")
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content
        raise RuntimeError("OpenRouter response missing message content")

    def get_model_limits(self) -> ModelLimits:
        model = self.settings.model.strip() or "unknown"
        try:
            infos = self.list_model_infos(purpose=ModelPurpose.text)
        except Exception:  # noqa: BLE001
            return ModelLimits(model=model)
        for item in infos:
            if item.id != model:
                continue
            if item.context_length and item.context_length > 0:
                return ModelLimits(
                    model=model,
                    context_length=item.context_length,
                    source="openrouter.models",
                )
            return ModelLimits(model=model)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self._base}/models",
                    headers=self._headers(),
                    params={"output_modalities": "all"},
                )
                _raise_for_status(response)
                payload = response.json()
        except Exception:  # noqa: BLE001
            return ModelLimits(model=model)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return ModelLimits(model=model)
        for raw in data:
            if not isinstance(raw, dict) or raw.get("id") != model:
                continue
            parsed = parse_openrouter_model(raw)
            if parsed and parsed.context_length:
                return ModelLimits(
                    model=model,
                    context_length=parsed.context_length,
                    source="openrouter.models",
                )
            return ModelLimits(model=model)
        return ModelLimits(model=model)

    def ping(self) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            models = self.list_models()
            latency = (time.perf_counter() - started) * 1000.0
            return ConnectionTestResult(
                ok=True,
                latency_ms=latency,
                message=f"ok · {len(models)} model(s) listed",
                model=self.settings.model,
                models=models[:50],
            )
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - started) * 1000.0
            return ConnectionTestResult(
                ok=False,
                latency_ms=latency,
                message=str(exc),
                model=self.settings.model,
            )

"""GigaChat HTTP client (OAuth + models), compatible with ai-forever/gigachat API."""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from rageval_llm_providers.ca import httpx_verify_arg
from rageval_llm_providers.catalog import (
    ModelPurpose,
    RemoteModelInfo,
    filter_gigachat_models,
    parse_gigachat_model,
)
from rageval_llm_providers.config import GigaChatSettings
from rageval_llm_providers.limits import ModelLimits
from rageval_llm_providers.protocol import ConnectionTestResult


class GigaChatProvider:
    def __init__(self, settings: GigaChatSettings, *, timeout: float = 30.0) -> None:
        self.settings = settings
        self.timeout = timeout
        self.generate_timeout = max(timeout, 180.0)

    def _token(self, client: httpx.Client) -> str:
        credentials = self.settings.credentials.strip()
        if not credentials:
            raise ValueError("GigaChat credentials (authorization key) are not configured")
        response = client.post(
            self.settings.auth_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"scope": self.settings.scope},
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("GigaChat OAuth response missing access_token")
        return token

    def _fetch_raw_models(self) -> list[dict[str, Any] | str]:
        verify = httpx_verify_arg(verify_ssl=self.settings.verify_ssl)
        with httpx.Client(timeout=self.timeout, verify=verify) as client:
            token = self._token(client)
            base = self.settings.base_url.rstrip("/")
            response = client.get(
                f"{base}/models",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data") or payload.get("models") or []
        return list(data) if isinstance(data, list) else []

    def list_model_infos(
        self, *, purpose: ModelPurpose = ModelPurpose.text
    ) -> list[RemoteModelInfo]:
        items: list[RemoteModelInfo] = []
        for raw in self._fetch_raw_models():
            parsed = parse_gigachat_model(raw)
            if parsed is not None:
                items.append(parsed)
        return filter_gigachat_models(items, purpose=purpose)

    def list_models(self) -> list[str]:
        return [m.id for m in self.list_model_infos(purpose=ModelPurpose.text)]

    def generate(
        self,
        prompt: str,
        *,
        response_format: dict[str, Any] | str | None = None,
    ) -> str:
        del response_format  # GigaChat has no portable JSON-schema format flag here.
        model = self.settings.model.strip()
        if not model:
            raise ValueError("GigaChat model is not configured")
        verify = httpx_verify_arg(verify_ssl=self.settings.verify_ssl)
        with httpx.Client(timeout=self.generate_timeout, verify=verify) as client:
            token = self._token(client)
            base = self.settings.base_url.rstrip("/")
            response = client.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("GigaChat response missing choices")
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content
        raise RuntimeError("GigaChat response missing message content")

    def get_model_limits(self) -> ModelLimits:
        model = self.settings.model.strip() or "unknown"
        return ModelLimits(model=model)

    def ping(self) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            models = self.list_models()
            latency = (time.perf_counter() - started) * 1000.0
            return ConnectionTestResult(
                ok=True,
                latency_ms=latency,
                message=f"ok · OAuth + models ({len(models)})",
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

"""Ollama HTTP client (list tags / ping / generate)."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from rageval_llm_providers.catalog import ModelPurpose, RemoteModelInfo, ollama_model_infos
from rageval_llm_providers.config import OllamaSettings
from rageval_llm_providers.limits import ModelLimits, context_length_from_ollama_show
from rageval_llm_providers.protocol import ConnectionTestResult

logger = logging.getLogger(__name__)


class OllamaProvider:
    def __init__(self, settings: OllamaSettings, *, timeout: float = 15.0) -> None:
        self.settings = settings
        self.timeout = timeout
        self.generate_timeout = max(timeout, 180.0)

    @property
    def _base(self) -> str:
        return self.settings.base_url.rstrip("/")

    def list_models(self) -> list[str]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self._base}/api/tags")
            response.raise_for_status()
            payload = response.json()
        models = payload.get("models") or []
        names: list[str] = []
        for item in models:
            name = item.get("name") if isinstance(item, dict) else None
            if isinstance(name, str) and name:
                names.append(name)
        return names

    def _embedding_lengths(self, names: list[str]) -> dict[str, int]:
        """Best-effort ``embedding_length`` via ``/api/show`` (bounded parallelism)."""
        from rageval_llm_providers.limits import embedding_length_from_ollama_show

        if not names:
            return {}

        def one(name: str) -> tuple[str, int | None]:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self._base}/api/show",
                        json={"name": name},
                    )
                    response.raise_for_status()
                    payload = response.json()
            except Exception:  # noqa: BLE001
                return name, None
            if not isinstance(payload, dict):
                return name, None
            dim, _src = embedding_length_from_ollama_show(payload)
            return name, dim

        out: dict[str, int] = {}
        workers = max(1, min(8, len(names)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(one, n) for n in names]
            for fut in as_completed(futures):
                try:
                    name, dim = fut.result()
                except Exception:  # noqa: BLE001
                    logger.debug("ollama show failed", exc_info=True)
                    continue
                if dim is not None and dim > 0:
                    out[name] = dim
        return out

    def list_model_infos(
        self, *, purpose: ModelPurpose = ModelPurpose.text
    ) -> list[RemoteModelInfo]:
        names = self.list_models()
        dims: dict[str, int] = {}
        if purpose is ModelPurpose.embeddings:
            dims = self._embedding_lengths(names)
        return ollama_model_infos(names, dimensions_by_id=dims)

    @staticmethod
    def _ollama_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            text = (response.text or "").strip()
            return text or f"HTTP {response.status_code}"
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, str) and err.strip():
                return err.strip()
        return (response.text or "").strip() or f"HTTP {response.status_code}"

    @staticmethod
    def _extract_assistant_text(payload: dict) -> tuple[str | None, str]:
        """Return (text, source) from chat/generate payload."""
        message = payload.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content, "message.content"
            # Thinking models may leave content empty and put the answer in thinking.
            thinking = message.get("thinking")
            if isinstance(thinking, str) and thinking.strip():
                return thinking, "message.thinking"
        response = payload.get("response")
        if isinstance(response, str) and response.strip():
            return response, "response"
        return None, "none"

    def get_model_limits(self) -> ModelLimits:
        model = self.settings.model.strip() or "unknown"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self._base}/api/show",
                    json={"name": model},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:  # noqa: BLE001
            return ModelLimits(model=model)
        if not isinstance(payload, dict):
            return ModelLimits(model=model)
        ctx, source = context_length_from_ollama_show(payload)
        return ModelLimits(model=model, context_length=ctx, source=source)

    def generate(
        self,
        prompt: str,
        *,
        response_format: dict[str, Any] | str | None = None,
    ) -> str:
        model = self.settings.model.strip()
        if not model:
            raise ValueError("Ollama model is not configured")
        # Question-prep JSON with long quotes easily exceeds 4k tokens; -1 = no cap
        # (Ollama still stops at context / model limits).
        options: dict[str, Any] = {
            "num_predict": -1 if response_format is not None else 8192,
        }
        if response_format is not None:
            # Lower temperature helps constrained decoding stay on-schema.
            options["temperature"] = 0
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            # qwen3 / thinking models otherwise may spend the budget on
            # "thinking" and return empty message.content.
            "think": False,
            "options": options,
        }
        if response_format is not None:
            body["format"] = response_format
        with httpx.Client(timeout=self.generate_timeout) as client:
            response = client.post(
                f"{self._base}/api/chat",
                json=body,
            )
            if response.status_code == 404:
                detail = self._ollama_error_detail(response)
                hint = ""
                try:
                    available = self.list_models()
                except Exception:  # noqa: BLE001
                    available = []
                if available:
                    sample = ", ".join(available[:8])
                    more = f" (+{len(available) - 8} more)" if len(available) > 8 else ""
                    hint = (
                        f" Model {model!r} is not installed in Ollama. "
                        f"Pick one on the Models → Text tab, e.g. {sample}{more}."
                    )
                else:
                    hint = (
                        f" Model {model!r} is not installed. "
                        f"Run `ollama pull {model}` on the host, or choose another model."
                    )
                raise RuntimeError(f"Ollama: {detail}.{hint}")
            if response.is_error:
                raise RuntimeError(
                    f"Ollama HTTP {response.status_code}: {self._ollama_error_detail(response)}"
                )
            payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Ollama response is not a JSON object")
        text, source = self._extract_assistant_text(payload)
        done_reason = payload.get("done_reason")
        prompt_eval = payload.get("prompt_eval_count")
        eval_count = payload.get("eval_count")
        if text:
            if done_reason == "length":
                raise RuntimeError(
                    "Ollama output truncated (done_reason=length"
                    f", prompt_tokens={prompt_eval}, eval_tokens={eval_count},"
                    f" chars={len(text)}). Increase context or shorten the corpus;"
                    " structured question prep needs a large num_predict budget."
                )
            return text
        raise RuntimeError(
            "Ollama response missing message content"
            f" (source={source}, done_reason={done_reason!r},"
            f" prompt_tokens={prompt_eval}, eval_tokens={eval_count})."
            " Try a shorter corpus or a model without empty thinking output."
        )

    def ping(self) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            models = self.list_models()
            latency = (time.perf_counter() - started) * 1000.0
            chosen = self.settings.model
            if chosen and models:
                names = set(models)
                aliases = {chosen, f"{chosen}:latest"}
                installed = bool(aliases & names) or any(
                    m == chosen or m.startswith(f"{chosen}:") for m in models
                )
                if not installed:
                    sample = ", ".join(models[:5])
                    suffix = "…" if len(models) > 5 else ""
                    hint = f"model {chosen!r} not in tags; available: {sample}{suffix}"
                else:
                    hint = f"ok · model {chosen}"
            elif chosen:
                hint = f"ok · model {chosen}"
            else:
                hint = f"ok · {len(models)} model(s)"
            return ConnectionTestResult(
                ok=True,
                latency_ms=latency,
                message=hint,
                model=chosen or (models[0] if models else None),
                models=models[:50],
            )
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - started) * 1000.0
            message = str(exc)
            lowered = message.lower()
            if "connection refused" in lowered or "errno 111" in lowered:
                host = self._base
                if "localhost" in host or "127.0.0.1" in host:
                    message = (
                        f"{message}. API cannot reach Ollama at {host}. "
                        "In Docker Compose use http://host.docker.internal:11435 "
                        "(ollama-proxy → host 127.0.0.1:11434), not localhost."
                    )
                elif ":11434" in host:
                    message = (
                        f"{message}. Direct host :11434 is unreachable from Docker "
                        "while Ollama binds 127.0.0.1. Use http://host.docker.internal:11435 "
                        "and ensure the ollama-proxy compose service is running."
                    )
                else:
                    message = (
                        f"{message}. Is Ollama running on the host, and is ollama-proxy "
                        f"forwarding to it? Expected Base URL {host}."
                    )
            elif "name or service not known" in lowered or "nodename nor servname" in lowered:
                message = (
                    f"{message}. Hostname unresolved — for Docker Compose ensure "
                    "extra_hosts includes host.docker.internal:host-gateway."
                )
            return ConnectionTestResult(
                ok=False,
                latency_ms=latency,
                message=message,
                model=self.settings.model,
            )

"""Unified LLM interface so application/agent code never imports a specific
provider SDK directly. Selected via LLM_PROVIDER / LLM_MODEL env vars.
"""
from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass, field

from app.core.config import get_settings

settings = get_settings()

_MAX_RETRIES = 4
_BASE_BACKOFF_SECONDS = 2.0


async def _post_with_retry(client, url: str, **kwargs):
    """Shared retry-with-backoff for HTTP-based providers (OpenAI, Groq and
    other OpenAI-compatible APIs). A 429 from a free/rate-limited tier is
    retried with exponential backoff (honoring `Retry-After` when the
    provider sends one) instead of failing the whole workflow outright.
    """
    import httpx

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.post(url, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code != 429 or attempt == _MAX_RETRIES - 1:
                # TEMP DEBUG: print the provider's actual error body so we can
                # see *why* a 400/other error happened instead of just the code.
                print(f"LLM ERROR {exc.response.status_code}: {exc.response.text}", flush=True)
                raise
            retry_after = exc.response.headers.get("retry-after")
            wait_seconds = float(retry_after) if retry_after else _BASE_BACKOFF_SECONDS * (2 ** attempt)
            await asyncio.sleep(wait_seconds)
    raise last_exc  # pragma: no cover


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    raw: dict = field(default_factory=dict)


class LLMProvider(abc.ABC):
    name: str

    def __init__(self, model: str, api_key: str | None):
        self.model = model
        self.api_key = api_key

    @abc.abstractmethod
    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse: ...


class OpenAIProvider(LLMProvider):
    name = "openai"

    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        import httpx

        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await _post_with_retry(
                client,
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    **kwargs,
                },
            )
            data = resp.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            input_tokens=data["usage"]["prompt_tokens"],
            output_tokens=data["usage"]["completion_tokens"],
            model=self.model,
            provider=self.name,
            raw=data,
        )


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        import httpx

        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        system = "\n".join(m.content for m in messages if m.role == "system") or None
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await _post_with_retry(
                client,
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": kwargs.pop("max_tokens", 1024),
                    "system": system,
                    "messages": turns,
                    **kwargs,
                },
            )
            data = resp.json()
        return LLMResponse(
            content="".join(b.get("text", "") for b in data.get("content", [])),
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"],
            model=self.model,
            provider=self.name,
            raw=data,
        )


class GeminiProvider(LLMProvider):
    name = "gemini"

    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        import httpx

        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        contents = [{"role": "user" if m.role != "assistant" else "model", "parts": [{"text": m.content}]}
                    for m in messages if m.role != "system"]
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json={"contents": contents})
            resp.raise_for_status()
            data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            content=text,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            model=self.model,
            provider=self.name,
            raw=data,
        )


class GroqProvider(LLMProvider):
    name = "groq"

    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        import httpx

        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await _post_with_retry(
                client,
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    **kwargs,
                },
            )
            data = resp.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            input_tokens=data["usage"]["prompt_tokens"],
            output_tokens=data["usage"]["completion_tokens"],
            model=self.model,
            provider=self.name,
            raw=data,
        )


class MockProvider(LLMProvider):
    """Deterministic provider used in tests and local dev without any API key."""

    name = "mock"

    def __init__(self, model: str = "mock-model", api_key: str | None = None, script: list[str] | None = None):
        super().__init__(model, api_key)
        self._script = script or []
        self._call_count = 0

    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        content = self._script[self._call_count] if self._call_count < len(self._script) else "{}"
        self._call_count += 1
        return LLMResponse(
            content=content, input_tokens=10, output_tokens=10, model=self.model, provider=self.name
        )


_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "mock": MockProvider,
}


def get_llm_provider(provider_name: str | None = None, model: str | None = None) -> LLMProvider:
    provider_name = provider_name or settings.LLM_PROVIDER
    model = model or settings.LLM_MODEL
    key_map = {
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "gemini": settings.GOOGLE_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "mock": None,
    }
    cls = _PROVIDERS.get(provider_name)
    if cls is None:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider_name}")
    return cls(model=model, api_key=key_map.get(provider_name))
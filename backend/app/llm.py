"""Talk to a chat LLM over the OpenAI-compatible HTTP API (Groq, Ollama, OpenAI, ...).

We use plain httpx instead of an SDK so you can see exactly what is sent and received.
"""

from functools import lru_cache
from typing import Protocol

import httpx

from app.config import get_settings


class LLMUnavailable(Exception):
    """The LLM couldn't answer: no API key, network error, rate limit, server error..."""


class LLMClient(Protocol):
    def complete(self, messages: list[dict]) -> str: ...


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0,
                 reasoning_effort: str = "", max_tokens: int = 1500,
                 transport: httpx.BaseTransport | None = None):
        self.model = model
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._max_tokens = max_tokens
        # `transport` lets tests swap in a fake server instead of the real internet.
        self._http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def complete(self, messages: list[dict]) -> str:
        if not self._api_key:
            raise LLMUnavailable("No LLM API key configured (set LLM_API_KEY in .env).")
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,              # low = stick closely to the sources, little creativity
            "max_tokens": self._max_tokens,  # caps length and protects the free quota
        }
        if self._reasoning_effort:
            body["reasoning_effort"] = self._reasoning_effort
            body["include_reasoning"] = False   # we only want the final answer back
        try:
            response = self._http.post(
                "/chat/completions", headers={"Authorization": f"Bearer {self._api_key}"}, json=body
            )
        except httpx.HTTPError as exc:      # timeouts, DNS failures, dropped connections...
            raise LLMUnavailable(f"Could not reach the LLM: {exc}") from exc

        if response.status_code == 429:
            raise LLMUnavailable("The LLM's free quota is used up for now. Please try again later.")
        if response.status_code >= 400:
            raise LLMUnavailable(f"LLM error {response.status_code}: {response.text[:200]}")

        try:
            content = response.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMUnavailable("The LLM returned a response we couldn't read.") from exc
        if not content.strip():
            # e.g. a reasoning model used its whole token budget thinking
            raise LLMUnavailable("The LLM returned an empty answer.")
        return content.strip()


@lru_cache
def get_llm() -> LLMClient:
    s = get_settings()
    return OpenAICompatibleClient(s.llm_base_url, s.llm_api_key, s.llm_model, s.llm_timeout_seconds,
                                  reasoning_effort=s.llm_reasoning_effort, max_tokens=s.llm_max_tokens)

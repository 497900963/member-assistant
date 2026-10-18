"""OpenAI-compatible LLM client with streaming.

The endpoint is fully configurable via env vars so production can point it at
the company's internally deployed model. Streams SSE-style text chunks.
"""
from __future__ import annotations

import json
from typing import Iterator

import httpx

from .config import settings
from .log import get_logger, log_with

logger = get_logger(__name__)


class LLMError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    return headers


def chat_stream(messages: list[dict[str, str]]) -> Iterator[str]:
    """Yield text deltas from a streaming chat completion."""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
    }
    try:
        with httpx.stream(
            "POST", url, headers=_headers(), json=payload, timeout=settings.llm_timeout
        ) as resp:
            if resp.status_code != 200:
                body = resp.read().decode("utf-8", "replace")[:500]
                raise LLMError(f"llm http {resp.status_code}: {body}")
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content", "")
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta
    except httpx.TimeoutException as e:
        raise LLMError(f"llm timeout after {settings.llm_timeout}s") from e
    except httpx.HTTPError as e:
        raise LLMError(f"llm transport error: {e}") from e


def chat_once(messages: list[dict[str, str]]) -> str:
    return "".join(chat_stream(messages))

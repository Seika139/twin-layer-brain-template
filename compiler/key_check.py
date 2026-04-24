from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass

import httpx

HeadersFactory = Callable[[str], dict[str, str]]


# Chat LLM providers used by `server/llm.py`. The /models endpoint is the
# cheapest liveness probe each vendor exposes.
_CHAT_PROVIDERS: dict[str, tuple[str, str, HeadersFactory]] = {
    "openai": (
        "OPENAI_API_KEY",
        "https://api.openai.com/v1/models",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
    "gemini": (
        "GEMINI_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/models",
        lambda key: {"x-goog-api-key": key},
    ),
    "anthropic": (
        "ANTHROPIC_API_KEY",
        "https://api.anthropic.com/v1/models",
        lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    ),
}


@dataclass(frozen=True)
class KeyStatus:
    provider: str
    env_var: str
    status: str  # "OK" | "RATE" | "AUTH" | "NONE" | "ERR"
    detail: str
    prefix: str


async def _check_one(
    provider: str,
    env_var: str,
    url: str,
    headers_factory: HeadersFactory,
) -> KeyStatus:
    key = os.environ.get(env_var, "")
    prefix = key[:4] + "..." if key else ""
    if not key:
        return KeyStatus(provider, env_var, "NONE", "env var not set", prefix)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers_factory(key), timeout=10.0)
    except httpx.HTTPError as e:
        return KeyStatus(provider, env_var, "ERR", f"network: {str(e)[:80]}", prefix)

    code = resp.status_code
    if code == 200:
        return KeyStatus(provider, env_var, "OK", "HTTP 200", prefix)
    if code == 429:
        return KeyStatus(
            provider, env_var, "RATE", "HTTP 429 rate limited (key valid)", prefix
        )
    if code in (401, 403):
        return KeyStatus(provider, env_var, "AUTH", f"HTTP {code} invalid key", prefix)
    return KeyStatus(provider, env_var, "ERR", f"HTTP {code}", prefix)


async def check_all_keys() -> list[KeyStatus]:
    """Concurrently probe all configured chat LLM providers."""
    tasks = [
        _check_one(provider, env_var, url, headers_factory)
        for provider, (env_var, url, headers_factory) in _CHAT_PROVIDERS.items()
    ]
    return await asyncio.gather(*tasks)

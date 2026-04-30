from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass

import httpx as httpx

from compiler.config import OPENAI_MODEL

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
    status: str  # "OK" | "RATE" | "AUTH" | "NONE" | "ERR" | "SKIP"
    detail: str
    prefix: str

    def is_usable(self) -> bool:
        """Return whether the checked capability is usable."""
        return self.status in ("OK", "RATE")

    def to_dict(self) -> dict[str, str | bool]:
        """Return a JSON-serializable representation."""
        return {
            "provider": self.provider,
            "env_var": self.env_var,
            "status": self.status,
            "detail": self.detail,
            "prefix": self.prefix,
            "usable": self.is_usable(),
        }


def _key_prefix(key: str) -> str:
    return key[:8] + "..." if key else ""


def _status_from_response(
    provider: str,
    env_var: str,
    prefix: str,
    resp: httpx.Response,
    ok_detail: str,
) -> KeyStatus:
    code = resp.status_code
    if code == 200:
        return KeyStatus(provider, env_var, "OK", ok_detail, prefix)
    if code == 429:
        return KeyStatus(
            provider, env_var, "RATE", "HTTP 429 rate limited (key valid)", prefix
        )
    if code in (401, 403):
        return KeyStatus(provider, env_var, "AUTH", f"HTTP {code} invalid key", prefix)

    detail = f"HTTP {code}"
    if resp.text:
        detail = f"{detail}: {resp.text[:120]}"
    return KeyStatus(provider, env_var, "ERR", detail, prefix)


async def _check_one(
    provider: str,
    env_var: str,
    url: str,
    headers_factory: HeadersFactory,
) -> KeyStatus:
    key = os.environ.get(env_var, "")
    prefix = _key_prefix(key)
    if not key:
        return KeyStatus(provider, env_var, "NONE", "env var not set", prefix)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers_factory(key), timeout=10.0)
    except httpx.HTTPError as e:
        return KeyStatus(provider, env_var, "ERR", f"network: {str(e)[:80]}", prefix)

    return _status_from_response(provider, env_var, prefix, resp, "HTTP 200")


async def check_embedding() -> KeyStatus:
    """Probe the exact OpenAI embedding endpoint used by semantic search."""
    provider = "openai-embed"
    env_var = "OPENAI_API_KEY"
    key = os.environ.get(env_var, "")
    prefix = _key_prefix(key)
    if not key:
        return KeyStatus(provider, env_var, "NONE", "env var not set", prefix)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": OPENAI_MODEL,
                    "input": "twin-layer-brain-template embedding key check",
                },
                timeout=10.0,
            )
    except httpx.HTTPError as e:
        return KeyStatus(provider, env_var, "ERR", f"network: {str(e)[:80]}", prefix)

    if resp.status_code != 200:
        return _status_from_response(
            provider,
            env_var,
            prefix,
            resp,
            f"{OPENAI_MODEL} embedding probe OK",
        )

    try:
        payload = resp.json()
    except ValueError:
        return KeyStatus(
            provider,
            env_var,
            "ERR",
            "HTTP 200 but response is not JSON",
            prefix,
        )

    data = payload.get("data")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            vector = first.get("embedding")
            if isinstance(vector, list) and vector:
                return KeyStatus(
                    provider,
                    env_var,
                    "OK",
                    f"{OPENAI_MODEL} embedding probe OK",
                    prefix,
                )

    return KeyStatus(
        provider,
        env_var,
        "ERR",
        "HTTP 200 but embedding vector was missing",
        prefix,
    )


async def check_all_keys() -> list[KeyStatus]:
    """Concurrently probe all configured chat LLM providers."""
    tasks = [
        _check_one(provider, env_var, url, headers_factory)
        for provider, (env_var, url, headers_factory) in _CHAT_PROVIDERS.items()
    ]
    return await asyncio.gather(*tasks)

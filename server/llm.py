from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import Any, cast

import httpx

from compiler.config import INDEX_DIR

logging.getLogger("httpx").setLevel(logging.WARNING)

LLM_PROVIDERS = ["openai", "gemini", "anthropic"]

_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

SYSTEM_PROMPT = (
    "You are a knowledge management assistant for a personal knowledge base.\n"
    "\n"
    "Given a web page's title, URL, and content, produce a JSON object with:\n"
    "\n"
    '1. "summary": A well-structured summary in Japanese using Markdown.\n'
    "   - Start with a 1-2 sentence overview of what this page is about.\n"
    "   - Then list the key points as bullet points (3-7 points).\n"
    "   - Focus on actionable knowledge, concrete facts, and unique insights.\n"
    "   - Ignore navigation, ads, footers, and boilerplate content.\n"
    "\n"
    '2. "tags": An array of 3-6 tags following these rules:\n'
    '   - Use lowercase, hyphenated compound words (e.g. "error-handling", "web-api")\n'
    '   - Include at least one CATEGORY tag (e.g. "programming", "devops", "design", "business", "math")\n'  # noqa: E501
    '   - Include at least one TOPIC tag specific to the content (e.g. "python", "docker", "react")\n'  # noqa: E501
    '   - Use Japanese tags only for Japan-specific topics (e.g. "確定申告")\n'
    "   - Prefer reusable tags over overly specific ones\n"
    "\n"
    "Respond ONLY with valid JSON. No markdown fences."
)

_CACHE_FILE = INDEX_DIR / "llm_provider_cache.json"


def _get_provider_order() -> list[str]:
    custom = os.environ.get("BRAIN_LLM_PRIORITY")
    if custom:
        return [p.strip().lower() for p in custom.split(",") if p.strip()]
    return LLM_PROVIDERS


def _read_cache() -> dict[str, Any] | None:
    if not _CACHE_FILE.exists():
        return None
    try:
        data = json.loads(_CACHE_FILE.read_text())
        if data.get("date") == str(date.today()):
            return cast(dict[str, Any], data)
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _write_cache(provider: str | None) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(
        json.dumps({"date": str(date.today()), "provider": provider})
    )


async def _check_openai(api_key: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        return resp.status_code in (200, 429)


async def _check_gemini(api_key: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": api_key},
            timeout=10.0,
        )
        return resp.status_code in (200, 429)


async def _check_anthropic(api_key: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=10.0,
        )
        return resp.status_code in (200, 429)


_HEALTH_CHECKS = {
    "openai": _check_openai,
    "gemini": _check_gemini,
    "anthropic": _check_anthropic,
}


async def _resolve_provider() -> tuple[str, str] | None:
    cache = _read_cache()
    if cache is not None:
        provider = cache.get("provider")
        if provider is None:
            return None
        key = os.environ.get(_KEY_MAP.get(provider, ""), "")
        if key:
            return provider, key

    for provider in _get_provider_order():
        env_var = _KEY_MAP.get(provider)
        if not env_var:
            continue
        key = os.environ.get(env_var, "")
        if not key:
            continue
        check = _HEALTH_CHECKS.get(provider)
        if check:
            try:
                ok = await check(key)
            except httpx.HTTPError:
                ok = False
            if not ok:
                continue
        _write_cache(provider)
        return provider, key

    _write_cache(None)
    return None


async def _call_openai(api_key: str, user_msg: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.3,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return cast(str, resp.json()["choices"][0]["message"]["content"])


async def _call_gemini(api_key: str, user_msg: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"x-goog-api-key": api_key},
            json={
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"parts": [{"text": user_msg}]}],
                "generationConfig": {"temperature": 0.3},
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return cast(str, resp.json()["candidates"][0]["content"]["parts"][0]["text"])


async def _call_anthropic(api_key: str, user_msg: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_msg}],
                "temperature": 0.3,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return cast(str, resp.json()["content"][0]["text"])


_CALLERS = {
    "openai": _call_openai,
    "gemini": _call_gemini,
    "anthropic": _call_anthropic,
}


async def summarize_page(title: str, url: str, content: str) -> dict[str, Any]:
    provider_info = await _resolve_provider()
    if provider_info is None:
        return {"summary": None, "tags": []}

    provider, api_key = provider_info
    truncated = content[:8000]
    user_msg = f"Title: {title}\nURL: {url}\n\nContent:\n{truncated}"

    caller = _CALLERS[provider]
    try:
        raw = await caller(api_key, user_msg)
    except httpx.HTTPError as e:
        msg = str(e).split("For more")[0].strip()
        logging.getLogger(__name__).warning("LLM call failed (%s): %s", provider, msg)
        return {"summary": None, "tags": []}

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"summary": raw, "tags": []}

    return {
        "summary": result.get("summary", ""),
        "tags": result.get("tags", []),
    }

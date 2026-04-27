from __future__ import annotations

import asyncio
from typing import Any

import httpx

from compiler import cli, key_check


class _FakeAsyncClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return self._response


def test_check_embedding_reports_none_when_openai_key_is_absent(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status = asyncio.run(key_check.check_embedding())

    assert status.provider == "openai-embed"
    assert status.env_var == "OPENAI_API_KEY"
    assert status.status == "NONE"


def test_check_embedding_probes_embedding_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_client() -> _FakeAsyncClient:
        return _FakeAsyncClient(
            httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})
        )

    monkeypatch.setattr(key_check.httpx, "AsyncClient", fake_client)

    status = asyncio.run(key_check.check_embedding())

    assert status.provider == "openai-embed"
    assert status.status == "OK"
    assert "embedding probe OK" in status.detail


def test_check_embedding_reports_auth_failure(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_client() -> _FakeAsyncClient:
        return _FakeAsyncClient(httpx.Response(401, text="invalid key"))

    monkeypatch.setattr(key_check.httpx, "AsyncClient", fake_client)

    status = asyncio.run(key_check.check_embedding())

    assert status.status == "AUTH"
    assert status.detail == "HTTP 401 invalid key"


def test_key_status_to_dict_includes_usable_flag() -> None:
    status = key_check.KeyStatus(
        provider="openai",
        env_var="OPENAI_API_KEY",
        status="OK",
        detail="HTTP 200",
        prefix="sk-test...",
    )

    assert status.to_dict() == {
        "provider": "openai",
        "env_var": "OPENAI_API_KEY",
        "status": "OK",
        "detail": "HTTP 200",
        "prefix": "sk-test...",
        "usable": True,
    }


def test_key_status_skip_is_not_usable() -> None:
    status = key_check.KeyStatus(
        provider="openai-embed",
        env_var="OPENAI_API_KEY",
        status="SKIP",
        detail="live embedding probe skipped",
        prefix="sk-test...",
    )

    assert status.is_usable() is False


def test_check_keys_formatter_can_colorize_badges() -> None:
    status = key_check.KeyStatus(
        provider="openai",
        env_var="OPENAI_API_KEY",
        status="OK",
        detail="HTTP 200",
        prefix="sk-test...",
    )

    rendered = cli._format_key_status(status, use_color=True)

    assert "\033[32m[ OK  ]\033[0m" in rendered

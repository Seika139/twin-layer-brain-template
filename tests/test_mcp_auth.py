from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from server.mcp_auth import McpBearerAuthMiddleware


async def ok_endpoint(_request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _test_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/mcp", ok_endpoint),
            Route("/api/health", ok_endpoint),
        ],
        middleware=[Middleware(McpBearerAuthMiddleware)],
    )


def test_mcp_auth_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("BRAIN_MCP_REQUIRE_TOKEN", raising=False)
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")

    res = TestClient(_test_app()).get("/mcp")

    assert res.status_code == 200


def test_mcp_auth_requires_bearer_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("BRAIN_MCP_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")

    res = TestClient(_test_app()).get("/mcp")

    assert res.status_code == 401


def test_mcp_auth_accepts_valid_bearer(monkeypatch) -> None:
    monkeypatch.setenv("BRAIN_MCP_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")

    res = TestClient(_test_app()).get(
        "/mcp",
        headers={"Authorization": "Bearer secret"},
    )

    assert res.status_code == 200


def test_mcp_auth_does_not_guard_rest_routes(monkeypatch) -> None:
    monkeypatch.setenv("BRAIN_MCP_REQUIRE_TOKEN", "true")

    res = TestClient(_test_app()).get("/api/health")

    assert res.status_code == 200

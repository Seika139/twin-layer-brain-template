from __future__ import annotations

import hmac
import os

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


def is_mcp_auth_required() -> bool:
    return os.environ.get("BRAIN_MCP_REQUIRE_TOKEN", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class McpBearerAuthMiddleware:
    """Optionally protect HTTP MCP endpoints with BRAIN_API_TOKEN."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not is_mcp_auth_required():
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not isinstance(path, str) or not (
            path == "/mcp" or path.startswith("/mcp/")
        ):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        response = _check_mcp_bearer(request)
        if response is not None:
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _check_mcp_bearer(request: Request) -> Response | None:
    expected = os.environ.get("BRAIN_API_TOKEN")
    if not expected:
        return JSONResponse(
            {"detail": "API token not configured on server"},
            status_code=503,
        )

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return JSONResponse({"detail": "Missing bearer token"}, status_code=401)

    if not hmac.compare_digest(token, expected):
        return JSONResponse({"detail": "Invalid token"}, status_code=403)

    return None

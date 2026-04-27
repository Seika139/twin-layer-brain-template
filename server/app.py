from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from server.mcp_auth import McpBearerAuthMiddleware
from server.mcp_server import mcp
from server.routes.auth_check import router as auth_check_router
from server.routes.clip import router as clip_router
from server.routes.index import router as index_router
from server.routes.notes import router as notes_router
from server.routes.sync import router as sync_router

# --- FastAPI (REST API) ---

fastapi_app = FastAPI(title="twin-layer-brain API", version="0.1.0")
fastapi_app.include_router(auth_check_router)
fastapi_app.include_router(notes_router)
fastapi_app.include_router(index_router)
fastapi_app.include_router(sync_router)
fastapi_app.include_router(clip_router)


@fastapi_app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Combined app (Starlette outer shell) ---


@contextlib.asynccontextmanager
async def lifespan(_app: Starlette) -> AsyncGenerator[None]:
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Mount("/api", app=fastapi_app),
        Mount("/mcp", app=mcp.streamable_http_app()),
        Mount("/mcp/", app=mcp.streamable_http_app()),
    ],
    middleware=[Middleware(McpBearerAuthMiddleware)],
    lifespan=lifespan,
)

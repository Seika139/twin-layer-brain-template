from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer()


def _get_api_token() -> str | None:
    return os.environ.get("BRAIN_API_TOKEN")


async def require_token(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Validate Bearer token. Raises 401/403 on failure."""
    expected = _get_api_token()
    if not expected:
        raise HTTPException(503, "API token not configured on server")
    if not hmac.compare_digest(creds.credentials, expected):
        raise HTTPException(403, "Invalid token")
    return creds.credentials


async def verify_webhook_signature(request: Request) -> None:
    """Validate GitHub webhook HMAC-SHA256 signature."""
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "Webhook secret not configured")

    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(400, "Missing signature header")

    body = await request.body()
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(403, "Invalid webhook signature")

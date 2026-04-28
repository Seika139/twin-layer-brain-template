from __future__ import annotations

import subprocess

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from compiler.indexer import rebuild_index
from compiler.paths import BASE_DIR
from server.auth import verify_webhook_signature

router = APIRouter(prefix="/sync")


class WebhookResponse(BaseModel):
    status: str
    indexed: int


@router.post("/webhook", dependencies=[Depends(verify_webhook_signature)])
async def webhook() -> WebhookResponse:
    subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=str(BASE_DIR),
        check=True,
        capture_output=True,
    )
    count = rebuild_index()
    return WebhookResponse(status="ok", indexed=count)

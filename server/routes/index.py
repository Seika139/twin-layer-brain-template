from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from compiler.indexer import rebuild_index
from server.auth import require_token

router = APIRouter(prefix="/index", dependencies=[Depends(require_token)])


class RebuildResponse(BaseModel):
    count: int
    message: str


@router.post("/rebuild")
async def rebuild() -> RebuildResponse:
    count = rebuild_index()
    return RebuildResponse(count=count, message=f"Indexed {count} notes")

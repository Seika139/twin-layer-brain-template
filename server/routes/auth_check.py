from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from server.auth import require_token

router = APIRouter(prefix="/auth")


class AuthCheckResponse(BaseModel):
    status: Literal["ok"]


@router.get("/check")
async def check_auth(_token: str = Depends(require_token)) -> AuthCheckResponse:
    return AuthCheckResponse(status="ok")

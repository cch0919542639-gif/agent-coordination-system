from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from services.coordination_api.config import Settings


async def verify_api_key(request: Request, settings: Settings) -> JSONResponse | None:
    if not settings.is_api_key_required:
        return None

    api_key = request.headers.get("X-API-Key", "")
    if api_key not in settings.api_keys:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or missing API key"},
        )
    return None

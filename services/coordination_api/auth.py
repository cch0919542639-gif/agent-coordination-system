from __future__ import annotations

from fastapi import HTTPException, Request, status

from services.coordination_api.config import Settings


async def verify_api_key(request: Request, settings: Settings) -> None:
    if not settings.is_api_key_required:
        return

    api_key = request.headers.get("X-API-Key", "")
    if api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

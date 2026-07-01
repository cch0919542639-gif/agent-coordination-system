from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.coordination_api.auth import verify_api_key
from services.coordination_api.config import Settings
from services.coordination_api.database import run_migrations
from services.coordination_api.routes import router

settings = Settings()
app = FastAPI(title="Coordination API", version="0.1.0")
app.include_router(router)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    await verify_api_key(request, settings)
    return await call_next(request)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "version": "0.1.0"})


def main() -> None:
    import uvicorn

    run_migrations()
    uvicorn.run(
        "services.coordination_api.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )

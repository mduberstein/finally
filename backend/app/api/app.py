from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.portfolio import router as portfolio_router
from app.api.stream import router as stream_router
from app.api.watchlist import router as watchlist_router
from app.app_state import app_lifespan_state
from app.config import STATIC_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    async for _ in app_lifespan_state(app):
        yield


def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly API", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    app.include_router(chat_router)
    app.include_router(stream_router)

    if STATIC_DIR.exists():
        app.mount("/_next", StaticFiles(directory=STATIC_DIR / "_next"), name="next")
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    else:
        # For unit/integration tests before frontend build, mount nothing.
        pass

    index_path = STATIC_DIR / "index.html"

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "_next/", "assets/")):
            raise HTTPException(status_code=404, detail="Not found")
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(
            status_code=404,
            detail="Frontend static assets not built. Run npm run build in frontend.",
        )

    return app


app = create_app()

"""FastAPI entrypoint for the Agency Intelligence backend."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import analytics, reports, system, avatars
from app.core.config import get_settings
from app.infloww.client import InflowwClient
from app.infloww.monitor import monitor
from app.store.db import Database
from app.sync.engine import SyncEngine


class RedactFilter(logging.Filter):
    """Belt-and-braces: scrub the API key from any log line, whatever logged it."""

    def filter(self, record: logging.LogRecord) -> bool:
        key = get_settings().infloww_api_key.get_secret_value()
        if key and len(key) >= 8:
            msg = record.getMessage()
            if key in msg:
                record.msg = msg.replace(key, "<redacted>")
                record.args = ()
        return True


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for h in logging.getLogger().handlers:
        h.addFilter(RedactFilter())
    logging.getLogger("httpx").setLevel(logging.WARNING)   # httpx INFO logs full URLs; keep quiet


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    s = get_settings()
    app.state.db = getattr(app.state, "db", None) or Database(s.database_path)
    app.state.monitor = monitor
    app.state.client = getattr(app.state, "client", None) or InflowwClient(s, monitor)
    app.state.sync = SyncEngine(app.state.db, app.state.client, s)
    app.state.sync.loop = asyncio.get_running_loop()
    task = asyncio.create_task(app.state.sync.background_loop()) if s.background_sync else None
    yield
    if task:
        task.cancel()
    await app.state.client.aclose()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Agency Intelligence API", version="1.0.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Authorization", "X-Dashboard-Token"])

    @app.middleware("http")
    async def security_headers(request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.exception_handler(Exception)
    async def unhandled(request, exc):  # never leak internals/credentials in error bodies
        logging.getLogger("app").exception("unhandled error on %s", request.url.path)
        return JSONResponse({"detail": "Internal error"}, status_code=500)

    app.include_router(system.router)
    app.include_router(analytics.router)
    app.include_router(reports.router)
    app.include_router(avatars.router)

    # Serve the built frontend (single-service deployment) if present.
    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            f = dist / path
            if path and f.is_file() and dist in f.resolve().parents:
                return FileResponse(f)
            return FileResponse(dist / "index.html")

    return app


app = create_app()

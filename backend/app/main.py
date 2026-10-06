"""FastAPI entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.api import router
from app.config import get_settings
from app.limits import RateLimited
from app.maintenance import cleanup

log = logging.getLogger("sourcetrail")


async def cleanup_forever(interval_minutes: int, ttl_hours: int) -> None:
    """Every hour: delete expired visitor workspaces. Runs alongside the web server."""
    while True:
        try:
            def run():
                with db.open_pool().connection() as conn:
                    return cleanup(conn, ttl_hours)
            # cleanup() is ordinary blocking code; run it in a worker thread so it
            # doesn't freeze the server while it works.
            workspaces, events = await asyncio.to_thread(run)
            if workspaces or events:
                log.info("cleanup: %d workspaces, %d usage events deleted", workspaces, events)
        except Exception:
            log.exception("cleanup failed; will retry next interval")
        await asyncio.sleep(interval_minutes * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    settings = get_settings()
    task = None
    if settings.cleanup_enabled:
        task = asyncio.create_task(cleanup_forever(settings.cleanup_interval_minutes,
                                                   settings.workspace_ttl_hours))
    yield
    if task:
        task.cancel()
    db.close_pool()


app = FastAPI(
    title="sourcetrail-rag",
    description="Multi-source RAG: hybrid search, reranking and verifiable citations.",
    lifespan=lifespan,
)
# Every API route lives under /api, leaving "/" free for the web page.
app.include_router(router, prefix="/api")


@app.exception_handler(RateLimited)
def rate_limited(request: Request, exc: RateLimited) -> JSONResponse:
    """Turn RateLimited (raised anywhere) into HTTP 429 + a Retry-After header."""
    return JSONResponse(status_code=429, content={"detail": str(exc)},
                        headers={"Retry-After": str(exc.retry_after)})


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "database": "ok" if db.ping() else "down"}


# Serve the built frontend (if it has been built). Mounted last, so /api/* and /health
# are matched first; everything else is looked up as a file in frontend/out.
_frontend = Path(get_settings().frontend_dir)
if not _frontend.is_absolute():
    _frontend = Path(__file__).resolve().parent.parent / _frontend
if _frontend.is_dir():
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")

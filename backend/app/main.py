"""FastAPI entry point."""

import asyncio
import ctypes
import ctypes.util
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.admin_api import router as admin_router
from app.api import router
from app.config import get_settings
from app.limits import RateLimited
from app.maintenance import cleanup
from app.monitoring import log_event
from app.telemetry import busy

log = logging.getLogger("sourcetrail")

# How long this server took to get ready (shown by /health). Empty if models load lazily.
STARTUP: dict[str, float] = {}


def preload_models() -> dict[str, float]:
    """Load the embedder and reranker now, timing each (later calls reuse them)."""
    from app.embed import get_embedder
    from app.rerank import get_reranker

    loaded = {}
    for name, load in (("embedder_ms", get_embedder), ("reranker_ms", get_reranker)):
        started = time.perf_counter()
        load()
        loaded[name] = round((time.perf_counter() - started) * 1000)
    return loaded


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
    started = time.perf_counter()
    db.open_pool()
    settings = get_settings()
    if settings.preload_models:
        # Before serving: Cloud Run holds the first request until this is done, and gives the
        # container extra CPU while it starts, so this is the cheapest moment to load them.
        STARTUP.update(await asyncio.to_thread(preload_models))
        STARTUP["ready_ms"] = round((time.perf_counter() - started) * 1000)
        log_event("startup", **STARTUP)
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
app.include_router(admin_router, prefix="/api/admin")


# Searching and indexing allocate and free a few hundred MB in the model runtime. glibc keeps
# freed memory for reuse, so the process sat at ~500 MB after a few questions, at the limit
# of a 512 MB server. Handing it back after each such request keeps it at ~380 MB.
_libc = ctypes.CDLL(ctypes.util.find_library("c")) if ctypes.util.find_library("c") else None
_TRIM_AFTER = ("/api/query", "/api/documents")


@app.middleware("http")
async def release_memory(request: Request, call_next):
    response = await call_next(request)
    if _libc is not None and hasattr(_libc, "malloc_trim") and request.url.path.startswith(_TRIM_AFTER):
        _libc.malloc_trim(0)
    return response


@app.exception_handler(RateLimited)
def rate_limited(request: Request, exc: RateLimited) -> JSONResponse:
    """Turn RateLimited (raised anywhere) into HTTP 429 + a Retry-After header."""
    return JSONResponse(status_code=429, content={"detail": str(exc)},
                        headers={"Retry-After": str(exc.retry_after)})


@app.get("/health")
@app.get("/api/health")
def health(response: Response) -> dict:
    """For visitors and uptime checks: ready, busy (still answering) or unavailable. Versions,
    model names and start-up times are in the admin overview, not here."""
    if not db.ping():
        response.status_code = 503
        return {"status": "unavailable"}
    return {"status": "busy" if busy() else "ready"}


@app.middleware("http")
async def private_admin(request: Request, call_next):
    """Admin pages and data: never cached by a browser or proxy, never indexed."""
    response = await call_next(request)
    if request.url.path.startswith(("/admin", "/api/admin")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


# Serve the built frontend (if it has been built). Mounted last, so /api/* and /health
# are matched first; everything else is looked up as a file in frontend/out.
_frontend = Path(get_settings().frontend_dir)
if not _frontend.is_absolute():
    _frontend = Path(__file__).resolve().parent.parent / _frontend
if _frontend.is_dir():
    @app.get("/admin", include_in_schema=False)
    def admin_page() -> FileResponse:
        """The admin shell: a sign-in form until /api/admin/session says otherwise. It holds no data."""
        return FileResponse(_frontend / "admin.html")

    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")

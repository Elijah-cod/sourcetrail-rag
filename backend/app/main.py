"""FastAPI entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(
    title="sourcetrail-rag",
    description="Multi-source RAG: hybrid search, reranking and verifiable citations.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": "ok" if db.ping() else "down"}

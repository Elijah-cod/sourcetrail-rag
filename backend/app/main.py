"""FastAPI entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(title="sourcetrail-rag", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": "ok" if db.ping() else "down"}

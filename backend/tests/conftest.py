"""Shared test helpers. pytest loads this file automatically."""

import hashlib
import math
import re

import psycopg
import pytest

from app.config import get_settings
from app.migrate import apply_migrations


class FakeEmbedder:
    """A tiny stand-in for the real model: fast, offline, deterministic.

    Each word is hashed into one of 384 slots, so texts sharing words get similar
    vectors. Crude, but enough to test storage and search without downloading a model.
    """

    dim = 384

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            slot = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim
            vector[slot] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def db():
    """A real Postgres connection whose changes are rolled back after each test."""
    try:
        conn = psycopg.connect(get_settings().database_url, autocommit=True, connect_timeout=2)
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable — run `docker compose up -d db` to include this test")
    with conn:
        apply_migrations(conn)
        with conn.transaction(force_rollback=True):   # undo everything the test did
            yield conn


@pytest.fixture
def workspace_id(db):
    return db.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]

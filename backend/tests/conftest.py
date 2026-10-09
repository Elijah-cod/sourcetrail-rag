"""Shared test helpers. pytest loads this file automatically."""

import hashlib
import math
import os
import re

# The hourly cleanup job would touch the real database during tests; keep it off.
os.environ.setdefault("CLEANUP_ENABLED", "false")

import psycopg
import pytest

from app.config import get_settings
from app.migrate import apply_migrations

# Integration tests need Postgres or the real models: `pytest -m "not integration"` runs the
# rest in seconds with no services. Without the services they skip, which is convenient
# locally but would let a broken database pass CI as "skipped". With REQUIRE_SERVICES=1 (CI's
# integration job) a skipped integration test fails instead.
INTEGRATION_FIXTURES = {"db", "embedder", "real_reranker"}
REQUIRE_SERVICES = os.environ.get("REQUIRE_SERVICES") == "1"


def pytest_collection_modifyitems(items):
    for item in items:
        if INTEGRATION_FIXTURES & set(item.fixturenames):
            item.add_marker(pytest.mark.integration)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if REQUIRE_SERVICES and report.skipped and item.get_closest_marker("integration"):
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else report.longrepr
        report.outcome = "failed"
        report.longrepr = f"REQUIRE_SERVICES=1, but this integration test was skipped: {reason}"
    return report


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


class FakeReranker:
    """Stand-in cross-encoder: score = number of question words found in the passage."""

    def score(self, question: str, passages: list[str]) -> list[float]:
        words = set(re.findall(r"[a-z0-9]+", question.lower()))
        return [float(len(words & set(re.findall(r"[a-z0-9]+", p.lower())))) for p in passages]


@pytest.fixture
def fake_reranker() -> FakeReranker:
    return FakeReranker()


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
            # Start every test with an empty usage log, so rate limits and the daily LLM cap
            # aren't affected by real app usage in this database (rolled back afterwards).
            conn.execute("DELETE FROM usage_events")
            yield conn


@pytest.fixture
def workspace_id(db):
    return db.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]

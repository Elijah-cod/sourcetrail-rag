"""Operational records for the admin area: one row per question and per document added.

Only metadata is kept (times, counts, outcome, an error category), never question, answer or
document text, and rows are deleted after TELEMETRY_RETENTION_DAYS (app/maintenance.py).
Recording never breaks a visitor's request: a failure here is logged and ignored.
"""

import json
import logging
import threading
from contextlib import contextmanager
from uuid import UUID

import psycopg

log = logging.getLogger("sourcetrail.telemetry")

# Questions being answered right now; the public health check reports "busy" at this many.
BUSY_AT = 2
_in_flight = 0
_lock = threading.Lock()


@contextmanager
def answering():
    global _in_flight
    with _lock:
        _in_flight += 1
    try:
        yield
    finally:
        with _lock:
            _in_flight -= 1


def busy() -> bool:
    return _in_flight >= BUSY_AT


def record_query(conn: psycopg.Connection, mode: str, status: str, total_ms: float, timings: dict[str, float],
                 parts: int = 0, missing: int = 0, sources: int = 0, citations: int = 0,
                 error: str | None = None) -> None:
    stages = {k: round(v, 1) for k, v in timings.items() if k != "total_ms"}
    _insert(conn, """
        INSERT INTO query_events (mode, status, parts, missing, sources, citations, total_ms, timings, error)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (mode, status, parts, missing, sources, citations, round(total_ms, 1), json.dumps(stages), error))


def record_ingest(conn: psycopg.Connection, source_type: str, ok: bool, duration_ms: float, chunks: int = 0,
                  characters: int = 0, warning: str | None = None, error: str | None = None,
                  document_id: UUID | None = None) -> None:
    _insert(conn, """
        INSERT INTO ingest_events (source_type, ok, chunks, characters, duration_ms, warning, error, document_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (source_type, ok, chunks, characters, round(duration_ms, 1), warning, error, document_id))


def _insert(conn: psycopg.Connection, sql: str, params: tuple) -> None:
    try:
        conn.execute(sql, params)
    except psycopg.Error:
        log.exception("could not record telemetry")

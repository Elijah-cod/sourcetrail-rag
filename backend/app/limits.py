"""Protection for a public site with no logins: rate limits, storage caps, LLM quota."""

import hashlib
from dataclasses import dataclass
from uuid import UUID

import psycopg
from fastapi import Request

from app.config import get_settings
from app.llm import LLMClient, LLMUnavailable


class RateLimited(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after      # seconds, sent to the browser as Retry-After


class CapacityExceeded(Exception):
    """A workspace would hold more documents/chunks than allowed."""


# ---------- who is asking? ----------

def client_ip(request: Request) -> str:
    if get_settings().trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for", "")
        # Each proxy *appends* the address it saw, so the last entry was added by our own
        # proxy (Render) and is the real client. Earlier entries can be faked by the client.
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def client_key(request: Request) -> str:
    """A stable, anonymous key per client: a hash of the IP, never the IP itself."""
    return hashlib.sha256(f"sourcetrail:{client_ip(request)}".encode()).hexdigest()[:32]


# ---------- rate limits ----------

def check_rate(conn: psycopg.Connection, kind: str, subject: str, limit: int, window_seconds: int) -> None:
    """Allow the action and record it, or raise RateLimited if `limit` was reached in the window."""
    row = conn.execute(
        """
        SELECT count(*), min(created_at)
        FROM usage_events
        WHERE kind = %s AND subject = %s AND created_at > now() - make_interval(secs => %s)
        """,
        (kind, subject, window_seconds),
    ).fetchone()
    count, oldest = row
    if count >= limit:
        # The window frees up a slot when its oldest event expires.
        wait = conn.execute("SELECT ceil(extract(epoch FROM %s + make_interval(secs => %s) - now()))",
                            (oldest, window_seconds)).fetchone()[0]
        raise RateLimited(f"Too many {kind} requests. Please wait a moment and try again.",
                          retry_after=max(1, int(wait)))
    conn.execute("INSERT INTO usage_events (kind, subject) VALUES (%s, %s)", (kind, subject))


# ---------- storage caps ----------

@dataclass
class Usage:
    documents: int
    chunks: int


def workspace_usage(conn: psycopg.Connection, workspace_id: UUID) -> Usage:
    documents, chunks = conn.execute(
        """
        SELECT count(DISTINCT d.id), count(c.id)
        FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
        WHERE d.workspace_id = %s
        """,
        (workspace_id,),
    ).fetchone()
    return Usage(documents=documents, chunks=chunks)


def check_can_add_document(conn: psycopg.Connection, workspace_id: UUID) -> int:
    """Raise if the workspace is full; otherwise return how many more chunks it may hold."""
    s = get_settings()
    usage = workspace_usage(conn, workspace_id)
    if usage.documents >= s.max_documents_per_workspace:
        raise CapacityExceeded(f"You can keep up to {s.max_documents_per_workspace} documents. "
                               "Delete one to add another.")
    return s.max_chunks_per_workspace - usage.chunks


# ---------- site-wide LLM quota ----------

class QuotaLLM:
    """Wraps an LLM client and counts its calls against the site-wide daily cap.

    Same interface as any LLMClient, so the rest of the code doesn't know it's there.
    When the cap is reached it raises LLMUnavailable, and ask() then shows the sources only.
    """

    def __init__(self, inner: LLMClient, conn: psycopg.Connection, per_day: int):
        self._inner, self._conn, self._per_day = inner, conn, per_day

    def complete(self, messages: list[dict]) -> str:
        try:
            check_rate(self._conn, "llm", "global", self._per_day, 24 * 3600)
        except RateLimited as exc:
            raise LLMUnavailable("The demo's daily AI-answer limit has been reached.") from exc
        return self._inner.complete(messages)

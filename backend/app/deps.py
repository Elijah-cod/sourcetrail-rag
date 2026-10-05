"""FastAPI dependencies: small functions that routes declare as parameters.

FastAPI calls them for each request and passes in the result. Tests replace them
(app.dependency_overrides) with fakes: a rolled-back DB connection, fake models...
"""

from collections.abc import Iterator
from uuid import UUID

import psycopg
from fastapi import Depends, Request, Response

from app import db
from app.config import get_settings
from app.store import DEMO_WORKSPACE_ID

COOKIE_NAME = "st_workspace"
COOKIE_MAX_AGE = 7 * 24 * 3600     # browser keeps the cookie a week (data cleanup comes in step 12)


def get_conn() -> Iterator[psycopg.Connection]:
    """Borrow a database connection from the pool for the duration of one request."""
    with db.open_pool().connection() as conn:
        yield conn      # code after `yield` runs when the request is finished


def _workspace_from_cookie(request: Request, conn: psycopg.Connection) -> UUID | None:
    """The visitor's workspace, if their cookie names a real, non-demo workspace."""
    raw = request.cookies.get(COOKIE_NAME)
    try:
        workspace_id = UUID(raw) if raw else None
    except ValueError:
        return None                       # garbage cookie: treat as a new visitor
    if workspace_id is None:
        return None
    row = conn.execute(
        "UPDATE workspaces SET last_seen_at = now() WHERE id = %s AND NOT is_demo RETURNING id",
        (workspace_id,),
    ).fetchone()
    return row[0] if row else None        # unknown or demo ID -> not yours


def optional_workspace(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> UUID | None:
    """For read-only routes: don't create a workspace just because someone looked."""
    return _workspace_from_cookie(request, conn)


def require_workspace(request: Request, response: Response,
                      conn: psycopg.Connection = Depends(get_conn)) -> UUID:
    """For routes that store data: reuse the visitor's workspace or create one + set the cookie."""
    existing = _workspace_from_cookie(request, conn)
    if existing:
        return existing
    workspace_id = conn.execute("INSERT INTO workspaces DEFAULT VALUES RETURNING id").fetchone()[0]
    response.set_cookie(
        COOKIE_NAME, str(workspace_id), max_age=COOKIE_MAX_AGE,
        httponly=True,                          # JavaScript can't read it (limits XSS damage)
        samesite="lax",                         # not sent on cross-site POSTs (limits CSRF)
        secure=get_settings().cookie_secure,    # HTTPS-only in production
    )
    return workspace_id


def searchable_workspaces(own: UUID | None) -> list[UUID]:
    """What a visitor may search: their own workspace (if any) plus the demo collection."""
    return [own, DEMO_WORKSPACE_ID] if own else [DEMO_WORKSPACE_ID]

"""Admin routes (/api/admin/*): sign-in, and read-only operational data.

Every data route depends on `require_admin`, which checks the signed session cookie against the
database: an unlinked page is not a lock, this is. Nothing here changes visitors' data.
"""

import csv
import io
import os
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import admin, db
from app.api import benchmark_results
from app.config import get_settings
from app.deps import get_usage_conn
from app.limits import client_key

router = APIRouter()
STARTED_AT = datetime.now(timezone.utc)

NOT_ACCEPTED = "That password was not accepted."
TOO_MANY = "Too many attempts. Try again in a few minutes."
EXPIRED = "Your admin session expired."


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=200)


def _set_cookie(response: Response, value: str, max_age: int) -> None:
    response.set_cookie(admin.COOKIE_NAME, value, max_age=max_age, httponly=True, samesite="strict",
                        secure=get_settings().cookie_secure, path="/")


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT, summary="Sign in with the admin password")
def login(body: Login, request: Request, response: Response,
          conn: psycopg.Connection = Depends(get_usage_conn)):
    stored = admin.configured_hash()
    if stored is None:                       # fail closed; the reason is in the server log
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Admin sign-in isn't available.")
    who = client_key(request)
    if admin.recent_failures(conn, who) >= get_settings().admin_login_attempts:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, TOO_MANY, headers={"Retry-After": "900"})
    if not admin.verify_password(body.password, stored):
        admin.record(conn, "login_failed", who)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NOT_ACCEPTED)
    cookie, _ = admin.start_session(conn)
    admin.record(conn, "login", who)
    _set_cookie(response, cookie, get_settings().admin_session_hours * 3600)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
def logout(request: Request, response: Response, conn: psycopg.Connection = Depends(get_usage_conn)):
    if admin.session_status(conn, request.cookies.get(admin.COOKIE_NAME))[0] == "valid":
        admin.record(conn, "logout", client_key(request))
    admin.end_session(conn, request.cookies.get(admin.COOKIE_NAME))
    response.delete_cookie(admin.COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


def require_admin(request: Request, response: Response,
                  conn: psycopg.Connection = Depends(get_usage_conn)) -> datetime:
    """The session's expiry, or 401 (expired sessions say so, and lose their cookie)."""
    cookie = request.cookies.get(admin.COOKIE_NAME)
    state, expires = admin.session_status(conn, cookie)
    if state == "valid":
        return expires
    if state == "expired":
        admin.record(conn, "expired")
        admin.end_session(conn, cookie)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, EXPIRED if state == "expired" else "Sign in to continue.",
                        headers={"Set-Cookie": f"{admin.COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=strict"})


@router.get("/session", summary="Whether the admin is signed in, and until when")
def session(expires: datetime = Depends(require_admin)) -> dict:
    return {"expires_at": expires}


def _period(days: int) -> str:
    return f"{days} days"


@router.get("/overview", summary="Service status and the headline numbers for a period")
def overview(days: int = Query(1, ge=1, le=30), _: datetime = Depends(require_admin),
             conn: psycopg.Connection = Depends(get_usage_conn)) -> dict:
    settings = get_settings()
    q = conn.execute("""
        SELECT count(*),
               count(*) FILTER (WHERE status = 'answered'),
               count(*) FILTER (WHERE status = 'not_found'),
               count(*) FILTER (WHERE missing > 0),
               count(*) FILTER (WHERE status IN ('error', 'llm_unavailable')),
               percentile_cont(0.5) WITHIN GROUP (ORDER BY total_ms) FILTER (WHERE status <> 'error'),
               percentile_cont(0.95) WITHIN GROUP (ORDER BY total_ms) FILTER (WHERE status <> 'error')
        FROM query_events WHERE created_at > now() - %s::interval""", (_period(days),)).fetchone()
    i = conn.execute("""
        SELECT count(*) FILTER (WHERE ok), count(*) FILTER (WHERE NOT ok),
               count(*) FILTER (WHERE ok AND warning IS NOT NULL)
        FROM ingest_events WHERE created_at > now() - %s::interval""", (_period(days),)).fetchone()
    failed_logins = conn.execute(
        "SELECT count(*) FROM admin_events WHERE kind = 'login_failed' AND created_at > now() - %s::interval",
        (_period(days),)).fetchone()[0]
    regression = (benchmark_results().get("regression") or {})
    from app.main import STARTUP  # set when the models finished loading
    return {
        "service": {
            "database": "ok" if db.ping() else "down",
            "models": "loaded" if STARTUP else "load on first use",
            "llm": "configured" if settings.llm_api_key else "no API key",
            "checked_at": datetime.now(timezone.utc),
            "started_at": STARTED_AT,
            "uptime_s": round((datetime.now(timezone.utc) - STARTED_AT).total_seconds()),
            "startup_ms": STARTUP,
        },
        "build": {
            "version": _version(),
            "revision": os.environ.get("K_REVISION"),        # Cloud Run's deployment name
            "commit": os.environ.get("BUILD_COMMIT"),
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.reranker_model,
        },
        "period_days": days,
        "queries": {"total": q[0], "answered": q[1], "refused": q[2], "missing_parts": q[3], "errors": q[4],
                    "p50_ms": q[5], "p95_ms": q[6]},
        "ingestion": {"ok": i[0], "failed": i[1], "warnings": i[2]},
        "failed_logins": failed_logins,
        "benchmark_run_at": regression.get("generated_at"),
        "retention": {"documents_hours": settings.workspace_ttl_hours,
                      "telemetry_days": settings.telemetry_retention_days,
                      "admin_events_days": settings.admin_event_retention_days},
    }


@router.get("/benchmarks", summary="Latest retrieval evaluation and regression benchmark results")
def benchmarks(_: datetime = Depends(require_admin)) -> dict:
    return benchmark_results()


QUERY_COLUMNS = ["id", "created_at", "mode", "status", "parts", "missing", "sources", "citations", "total_ms",
                 "timings", "error"]
INGEST_COLUMNS = ["id", "created_at", "source_type", "ok", "chunks", "characters", "duration_ms", "warning",
                  "error", "expires_at"]


def _queries(conn: psycopg.Connection, days: int, limit: int) -> list[dict]:
    rows = conn.execute(f"""
        SELECT {', '.join(QUERY_COLUMNS)} FROM query_events
        WHERE created_at > now() - %s::interval ORDER BY created_at DESC LIMIT %s""",
                        (_period(days), limit)).fetchall()
    return [dict(zip(QUERY_COLUMNS, row, strict=True)) for row in rows]


def _ingestion(conn: psycopg.Connection, days: int, limit: int) -> list[dict]:
    # A document lasts until its workspace has been idle for the TTL (app/maintenance.py).
    rows = conn.execute("""
        SELECT e.id, e.created_at, e.source_type, e.ok, e.chunks, e.characters, e.duration_ms, e.warning,
               e.error, w.last_seen_at + make_interval(hours => %s)
        FROM ingest_events e
        LEFT JOIN documents d ON d.id = e.document_id
        LEFT JOIN workspaces w ON w.id = d.workspace_id
        WHERE e.created_at > now() - %s::interval ORDER BY e.created_at DESC LIMIT %s""",
                        (get_settings().workspace_ttl_hours, _period(days), limit)).fetchall()
    return [dict(zip(INGEST_COLUMNS, row, strict=True)) for row in rows]


@router.get("/queries", summary="Recent questions: outcome and time per stage (no question text)")
def queries(days: int = Query(1, ge=1, le=30), limit: int = Query(200, ge=1, le=1000),
            _: datetime = Depends(require_admin), conn: psycopg.Connection = Depends(get_usage_conn)) -> list[dict]:
    return _queries(conn, days, limit)


@router.get("/ingestion", summary="Recent uploads and pages: outcome, size, warnings (no content)")
def ingestion(days: int = Query(1, ge=1, le=30), limit: int = Query(200, ge=1, le=1000),
              _: datetime = Depends(require_admin), conn: psycopg.Connection = Depends(get_usage_conn)) -> list[dict]:
    return _ingestion(conn, days, limit)


@router.get("/export/{table}.csv", summary="Download queries, ingestion or benchmark results as CSV")
def export(table: str, days: int = Query(7, ge=1, le=30), _: datetime = Depends(require_admin),
           conn: psycopg.Connection = Depends(get_usage_conn)) -> StreamingResponse:
    if table == "queries":
        rows = _queries(conn, days, 100_000)
        for row in rows:                       # one column per stage, so spreadsheets can sum them
            row.update({f"{k}": v for k, v in (row.pop("timings") or {}).items()})
    elif table == "ingestion":
        rows = _ingestion(conn, days, 100_000)
    elif table == "benchmarks":
        regression = benchmark_results().get("regression") or {}
        rows = [{"run_at": regression.get("generated_at"), **{k: v for k, v in q.items() if not isinstance(v, (list, dict))},
                 "uncovered": "; ".join(q.get("uncovered") or [])} for q in regression.get("questions", [])]
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown export.")
    out = io.StringIO()
    columns = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: v.isoformat() if isinstance(v, datetime) else v for k, v in row.items()})
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="sourcetrail-{table}-{stamp}Z.csv"'})


def _version() -> str:
    try:
        return version("sourcetrail-rag")
    except PackageNotFoundError:
        return "0.1.0"

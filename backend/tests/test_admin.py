"""The admin area: one password, signed sessions, and data only for a valid session."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import admin, deps
from app.config import get_settings
from app.main import app

PASSWORD = "correct horse battery staple"
SECRET = "test-session-secret-0123456789abcdef"
DATA_ROUTES = ["/api/admin/session", "/api/admin/overview", "/api/admin/benchmarks", "/api/admin/queries",
               "/api/admin/ingestion", "/api/admin/export/queries.csv", "/api/admin/export/ingestion.csv",
               "/api/admin/export/benchmarks.csv"]


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", admin.hash_password(PASSWORD))
    monkeypatch.setenv("ADMIN_SESSION_SECRET", SECRET)
    get_settings.cache_clear()
    admin.configured_hash.cache_clear()
    yield
    get_settings.cache_clear()
    admin.configured_hash.cache_clear()


@pytest.fixture
def client(db, configured):
    app.dependency_overrides[deps.get_conn] = lambda: db
    app.dependency_overrides[deps.get_usage_conn] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def sign_in(client, password=PASSWORD):
    return client.post("/api/admin/login", json={"password": password})


def test_password_hash_verifies_only_the_right_password():
    stored = admin.hash_password(PASSWORD)
    assert stored.startswith("scrypt$") and PASSWORD not in stored
    assert admin.verify_password(PASSWORD, stored)
    assert not admin.verify_password(PASSWORD + "x", stored)
    assert not admin.verify_password(PASSWORD, "garbage")
    assert admin.hash_password(PASSWORD) != stored          # salted


@pytest.mark.parametrize("route", DATA_ROUTES)
def test_every_admin_route_refuses_without_a_session(client, route):
    assert client.get(route).status_code == 401


def test_wrong_password_creates_no_session(client, db):
    response = sign_in(client, "wrong password")
    assert response.status_code == 401 and response.json()["detail"] == "That password was not accepted."
    assert admin.COOKIE_NAME not in response.cookies
    assert db.execute("SELECT count(*) FROM admin_sessions").fetchone()[0] == 0


def test_correct_password_opens_the_admin_data_until_logout(client, db):
    response = sign_in(client)
    assert response.status_code == 204
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie
    for route in DATA_ROUTES:
        assert client.get(route).status_code == 200, route
    overview = client.get("/api/admin/overview")
    assert overview.headers["cache-control"] == "no-store" and "noindex" in overview.headers["x-robots-tag"]
    assert client.post("/api/admin/logout").status_code == 204
    assert client.get("/api/admin/overview").status_code == 401
    kinds = [k for (k,) in db.execute("SELECT kind FROM admin_events ORDER BY id")]
    assert kinds == ["login", "logout"]


def test_a_logged_out_cookie_stays_invalid_if_replayed(client):
    sign_in(client)
    stolen = client.cookies.get(admin.COOKIE_NAME)
    client.post("/api/admin/logout")
    replay = TestClient(app, cookies={admin.COOKIE_NAME: stolen})
    assert replay.get("/api/admin/overview").status_code == 401


def test_a_modified_cookie_is_refused(client):
    sign_in(client)
    token, signature = client.cookies.get(admin.COOKIE_NAME).rsplit(".", 1)
    forged = TestClient(app, cookies={admin.COOKIE_NAME: f"{token}x.{signature}"})
    assert forged.get("/api/admin/overview").status_code == 401


def test_changing_the_session_secret_signs_everyone_out(client, monkeypatch):
    sign_in(client)
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "a-different-secret-entirely-0987654321")
    get_settings.cache_clear()
    assert client.get("/api/admin/overview").status_code == 401


def test_an_expired_session_says_so(client, db):
    sign_in(client)
    db.execute("UPDATE admin_sessions SET expires_at = %s", (datetime.now(timezone.utc) - timedelta(seconds=1),))
    response = client.get("/api/admin/overview")
    assert response.status_code == 401 and response.json()["detail"] == "Your admin session expired."
    assert "expired" in [k for (k,) in db.execute("SELECT kind FROM admin_events")]


def test_sessions_last_twelve_hours(client, db):
    sign_in(client)
    expires = db.execute("SELECT expires_at FROM admin_sessions").fetchone()[0]
    assert timedelta(hours=11, minutes=59) < expires - datetime.now(timezone.utc) <= timedelta(hours=12)


def test_failed_sign_ins_are_rate_limited(client):
    for _ in range(get_settings().admin_login_attempts):
        assert sign_in(client, "guess").status_code == 401
    blocked = sign_in(client)                                  # even the right password, for now
    assert blocked.status_code == 429 and blocked.json()["detail"] == "Too many attempts. Try again in a few minutes."


def test_admin_stays_closed_without_configuration(db, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "")
    get_settings.cache_clear()
    admin.configured_hash.cache_clear()
    app.dependency_overrides[deps.get_usage_conn] = lambda: db
    try:
        with TestClient(app) as c:
            assert c.post("/api/admin/login", json={"password": "anything"}).status_code == 503
            assert c.get("/api/admin/overview").status_code == 401
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        admin.configured_hash.cache_clear()


def test_secrets_never_appear_in_responses(client):
    sign_in(client)
    for route in DATA_ROUTES + ["/health"]:
        text = client.get(route).text
        assert SECRET not in text and PASSWORD not in text and "scrypt$" not in text, route


def test_query_rows_hold_timings_but_no_question_text(client, db):
    db.execute("""INSERT INTO query_events (mode, status, parts, sources, citations, total_ms, timings)
                  VALUES ('hybrid_rerank', 'answered', 2, 4, 2, 812.5, '{"rerank_ms": 300}')""")
    sign_in(client)
    rows = client.get("/api/admin/queries").json()
    assert rows[0]["timings"] == {"rerank_ms": 300} and rows[0]["total_ms"] == 812.5
    assert "question" not in rows[0]
    overview = client.get("/api/admin/overview").json()
    assert overview["queries"]["total"] >= 1 and overview["build"]["embedding_model"]
    csv_text = client.get("/api/admin/export/queries.csv").text
    assert csv_text.splitlines()[0].startswith("id,created_at,mode,status") and "rerank_ms" in csv_text.splitlines()[0]

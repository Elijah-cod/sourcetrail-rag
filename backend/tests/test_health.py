from fastapi.testclient import TestClient

from app import db, telemetry
from app.main import app


def test_health_says_ready_and_nothing_about_the_system(monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: True)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}       # no versions, models or timings for visitors


def test_health_says_busy_while_answering_several_questions(monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: True)
    monkeypatch.setattr(telemetry, "_in_flight", telemetry.BUSY_AT)
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "busy"}


def test_health_reports_unavailable_when_the_database_is_down(monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: False)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 503 and response.json() == {"status": "unavailable"}


def test_models_are_loaded_before_serving_when_asked(monkeypatch):
    from app import main
    from app.config import get_settings

    loaded = []
    monkeypatch.setattr(db, "ping", lambda: True)
    monkeypatch.setattr(main, "preload_models", lambda: loaded.append(1) or {"embedder_ms": 5, "reranker_ms": 7})
    monkeypatch.setattr(main, "STARTUP", {})
    monkeypatch.setenv("PRELOAD_MODELS", "true")
    monkeypatch.setenv("CLEANUP_ENABLED", "false")
    get_settings.cache_clear()
    try:
        with TestClient(app):
            pass
    finally:
        get_settings.cache_clear()
    assert loaded == [1]
    assert main.STARTUP["embedder_ms"] == 5 and main.STARTUP["reranker_ms"] == 7 and main.STARTUP["ready_ms"] >= 0

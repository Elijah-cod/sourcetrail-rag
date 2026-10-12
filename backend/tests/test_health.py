from fastapi.testclient import TestClient

from app import db
from app.main import app


def test_health_reports_database_ok(monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: True)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "startup": {}}


def test_health_reports_database_down(monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: False)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "down", "startup": {}}


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
        with TestClient(app) as client:
            startup = client.get("/health").json()["startup"]
    finally:
        get_settings.cache_clear()
    assert loaded == [1]
    assert startup["embedder_ms"] == 5 and startup["reranker_ms"] == 7 and startup["ready_ms"] >= 0

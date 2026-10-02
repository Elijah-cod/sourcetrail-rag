from fastapi.testclient import TestClient

from app import db
from app.main import app


def test_health_reports_database_ok(monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: True)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_database_down(monkeypatch):
    monkeypatch.setattr(db, "ping", lambda: False)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "down"}

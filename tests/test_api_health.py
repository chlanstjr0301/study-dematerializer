"""
Tests for GET /api/health.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_content_type_json():
    resp = client.get("/api/health")
    assert "application/json" in resp.headers["content-type"]

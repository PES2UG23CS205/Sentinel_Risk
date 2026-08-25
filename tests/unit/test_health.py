"""
SentinelRisk — Backend Unit Tests: Health Endpoint

Verifies:
  - GET /health returns HTTP 200 with correct payload
  - GET / returns service info
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_service_name(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["service"] == "sentinelrisk"

    def test_health_returns_version(self, client):
        response = client.get("/health")
        data = response.json()
        assert "version" in data


class TestRootEndpoint:
    """Tests for GET /."""

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_service_info(self, client):
        response = client.get("/")
        data = response.json()
        assert data["service"] == "SentinelRisk"
        assert data["stage"] == 1

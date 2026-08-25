"""
SentinelRisk — Integration Tests: API Configuration

Verifies:
  - CORS headers are present
  - Placeholder endpoints return not_implemented
  - API structure is discoverable
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestCORSConfiguration:
    """Verify CORS is configured for frontend access."""

    def test_cors_allows_localhost_3000(self, client):
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestPlaceholderEndpoints:
    """Verify remaining placeholder endpoints return not_implemented."""

    @pytest.mark.parametrize("path", [
        "/events/",
        "/model/",
    ])
    def test_placeholder_returns_not_implemented(self, client, path):
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_implemented"
        assert data["stage"] == 1

    def test_production_endpoints_active(self, client):
        res_cases = client.get("/cases/")
        assert res_cases.status_code == 200
        assert "total_cases" in res_cases.json()

        res_inc = client.get("/incidents/scenarios")
        assert res_inc.status_code == 200
        assert "scenarios" in res_inc.json()

        res_metrics = client.get("/metrics/operations")
        assert res_metrics.status_code == 200
        assert "traffic" in res_metrics.json()

        res_ready = client.get("/health/ready")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] == "READY"


class TestAPIStructure:
    """Verify the API has discoverable OpenAPI docs."""

    def test_openapi_schema_available(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "SentinelRisk"

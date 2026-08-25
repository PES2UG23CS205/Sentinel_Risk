"""
SentinelRisk — Dashboard API & UI Integration Regression Tests

Verifies:
  - GET /dashboard serves HTML with properly scoped panel references in JS
  - POST /dashboard/evaluate-scenario/LEGITIMATE_TRANSACTION returns APPROVE payload
  - POST /dashboard/evaluate-scenario/ACCOUNT_TAKEOVER returns HOLD + ATO Investigation
  - POST /dashboard/evaluate-scenario/COORDINATED_ABUSE_RING returns HOLD + Graph Topology
  - POST /dashboard/evaluate-scenario/CARD_TESTING returns HOLD + Velocity Burst
  - POST /dashboard/evaluate-scenario/WHAT_BROKE_AT_2AM returns Incident Simulation
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestDashboardAPIAndScenarios:
    """Test dashboard endpoint and scenario evaluation contracts."""

    def test_dashboard_html_rendering_and_panel_scope(self, client):
        res = client.get("/dashboard")
        assert res.status_code == 200
        html = res.text
        assert "SentinelRisk Operations Console" in html
        assert "view-container" in html
        assert "detail-panel" in html

    def test_evaluate_legitimate_scenario(self, client):
        res = client.post("/dashboard/evaluate-scenario/LEGITIMATE_TRANSACTION")
        assert res.status_code == 200
        d = res.json()
        assert d["type"] == "TRANSACTION_EVALUATION"
        assert d["scenario_key"] == "LEGITIMATE_TRANSACTION"
        assert d["evaluation"]["decision"] == "APPROVE"
        assert d["evaluation"]["is_intervention"] == 0

    def test_evaluate_ato_scenario(self, client):
        res = client.post("/dashboard/evaluate-scenario/ACCOUNT_TAKEOVER")
        assert res.status_code == 200
        d = res.json()
        assert d["type"] == "TRANSACTION_EVALUATION"
        assert d["scenario_key"] == "ACCOUNT_TAKEOVER"
        assert d["evaluation"]["decision"] == "HOLD"
        assert d["evaluation"]["is_intervention"] == 1
        assert d["case"]["priority"] == "CRITICAL"
        assert d["investigation"]["investigation_status"] == "COMPLETED"
        assert len(d["investigation"]["findings"]) > 0

    def test_evaluate_ring_scenario(self, client):
        res = client.post("/dashboard/evaluate-scenario/COORDINATED_ABUSE_RING")
        assert res.status_code == 200
        d = res.json()
        assert d["type"] == "TRANSACTION_EVALUATION"
        assert d["scenario_key"] == "COORDINATED_ABUSE_RING"
        assert d["evaluation"]["decision"] == "HOLD"
        assert d["graph_topology"]["ring_score"] == 0.88
        assert len(d["graph_topology"]["connected_customers"]) == 6

    def test_evaluate_card_testing_scenario(self, client):
        res = client.post("/dashboard/evaluate-scenario/CARD_TESTING")
        assert res.status_code == 200
        d = res.json()
        assert d["type"] == "TRANSACTION_EVALUATION"
        assert d["scenario_key"] == "CARD_TESTING"
        assert d["evaluation"]["decision"] == "HOLD"
        assert d["case"] is not None

    def test_evaluate_what_broke_at_2am_scenario(self, client):
        res = client.post("/dashboard/evaluate-scenario/WHAT_BROKE_AT_2AM")
        assert res.status_code == 200
        d = res.json()
        assert d["type"] == "INCIDENT_SIMULATION"
        assert d["data"]["metrics"]["total_transactions"] == 20
        assert d["data"]["metrics"]["hold_count"] >= 15
        assert len(d["data"]["recovery_recommendations"]) >= 2

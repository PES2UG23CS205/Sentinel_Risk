"""
SentinelRisk — Integration Tests for Fraud Detection Handbook Replay API

Verifies:
  - GET /stream/external/fraud-handbook/metadata returns valid metadata and schema
  - POST /stream/external/fraud-handbook/load loads records into live session
  - POST /stream/step processes a transaction and updates live state
  - GET /stream/live-state returns replay metrics and confusion matrix
  - POST /stream/clear resets session state
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestFraudHandbookReplayAPI:
    """Integration test suite for external dataset streaming endpoints."""

    def test_get_external_metadata(self, client):
        res = client.get("/stream/external/fraud-handbook/metadata")
        assert res.status_code == 200
        data = res.json()
        assert data["available"] is True
        assert data["total_files"] == 183
        assert data["total_rows"] == 1754155
        assert data["total_fraud"] == 14681
        assert "schema_mapping_info" in data
        assert "component_compatibility" in data

    def test_load_and_step_replay_session(self, client):
        # 1. Clear session first
        client.post("/stream/clear")

        # 2. Load 50 transactions
        res_load = client.post("/stream/external/fraud-handbook/load", json={"limit": 50})
        assert res_load.status_code == 200
        load_data = res_load.json()
        assert load_data["status"] == "LOADED"
        assert load_data["rows_loaded"] == 50
        assert load_data["state"]["progress"]["total_rows"] == 50

        # 3. Step 5 events
        for _ in range(5):
            res_step = client.post("/stream/step")
            assert res_step.status_code == 200
            step_data = res_step.json()
            assert step_data["event"] is not None
            assert step_data["event"]["decision"] in ("APPROVE", "CHALLENGE", "REVIEW", "HOLD")

        # 4. Check live state
        res_state = client.get("/stream/live-state")
        assert res_state.status_code == 200
        state = res_state.json()
        assert state["counters"]["total_processed"] == 5
        assert state["replay_metrics"]["has_ground_truth"] is True
        assert (
            state["replay_metrics"]["tp"] +
            state["replay_metrics"]["fp"] +
            state["replay_metrics"]["tn"] +
            state["replay_metrics"]["fn"]
        ) == 5

        # 5. Clear
        res_clear = client.post("/stream/clear")
        assert res_clear.status_code == 200
        state_cleared = client.get("/stream/live-state").json()
        assert state_cleared["counters"]["total_processed"] == 0

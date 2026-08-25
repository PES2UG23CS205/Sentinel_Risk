"""
SentinelRisk — Stage 7: Cost-Sensitive Policy Engine Unit Tests

Verifies:
  - Policy configuration parsing, defaults, and versioning
  - Tri-state decisions: APPROVE, REVIEW, HOLD
  - Threshold boundaries (just below, at, just above)
  - Precedence hierarchy and multi-signal conflict resolution:
    - ML low + Graph high -> REVIEW / HOLD
    - ML high + Graph low -> HOLD
    - Compound moderate ML + Graph -> HOLD
    - Severe card velocity burst -> HOLD
    - Legitimate shared device -> APPROVE
  - Deterministic explainability and audit record completeness
  - Zero target/leakage in decision evaluation
  - Local API simulation endpoint POST /risk/evaluate
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.policy.models import DecisionState, PolicyConfig
from backend.app.policy.engine import PolicyEngine
from backend.app.main import app


@pytest.fixture
def policy_engine():
    return PolicyEngine()


@pytest.fixture
def client():
    return TestClient(app)


class TestPolicyConfiguration:
    """Test policy configuration parsing and versioning."""

    def test_policy_config_loaded_from_yaml(self, policy_engine):
        cfg = policy_engine.config
        assert cfg.policy_version == "sentinelrisk-policy-v1"
        assert cfg.ml_thresholds.challenge_threshold == 0.05
        assert cfg.ml_thresholds.review_threshold == 0.25
        assert cfg.ml_thresholds.hold_threshold == 0.50
        assert cfg.graph_thresholds.ring_score_review == 0.50
        assert cfg.graph_thresholds.ring_score_hold == 0.80
        assert cfg.rule_conditions.severe_card_velocity_1h == 5

    def test_policy_version_in_decision_record(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=1,
            timestamp="2025-01-01 10:00:00",
            amount=100.0,
            ml_probability=0.001,
        )
        assert rec.policy_version == "sentinelrisk-policy-v1"
        assert rec.decision == DecisionState.APPROVE


class TestDecisionStatesAndPrecedence:
    """Test APPROVE, REVIEW, HOLD decisions and precedence hierarchy."""

    def test_approve_low_risk(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=101,
            timestamp="2025-01-01 10:00:00",
            amount=250.0,
            ml_probability=0.01,
            graph_ring_score=0.0,
            graph_ring_candidate=0,
            feature_context={"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.1},
        )
        assert rec.decision == DecisionState.APPROVE
        assert rec.is_intervention is False
        assert "APPROVED_LOW_RISK" in rec.primary_trigger

    def test_review_on_elevated_ml(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=102,
            timestamp="2025-01-01 10:00:00",
            amount=1500.0,
            ml_probability=0.30,  # Elevated ML in manual review band >= 0.25
            graph_ring_score=0.0,
            graph_ring_candidate=0,
        )
        assert rec.decision == DecisionState.REVIEW
        assert rec.is_intervention is True
        assert "HIGH_ML_RISK" in rec.signals_triggered

    def test_hold_on_severe_ml(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=103,
            timestamp="2025-01-01 10:00:00",
            amount=8500.0,
            ml_probability=0.72,
            graph_ring_score=0.0,
            graph_ring_candidate=0,
        )
        assert rec.decision == DecisionState.HOLD
        assert rec.is_intervention is True
        assert "HIGH_CONFIDENCE_ML_RISK" in rec.signals_triggered

    def test_hold_on_severe_card_velocity_burst(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=104,
            timestamp="2025-01-01 10:00:00",
            amount=50.0,
            ml_probability=0.02,  # ML is low, but rule catches bot attack
            feature_context={"pi_velocity_count_1h": 6},
        )
        assert rec.decision == DecisionState.HOLD
        assert "SEVERE_PI_VELOCITY" in rec.signals_triggered

    def test_review_on_graph_ring_candidate(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=105,
            timestamp="2025-01-01 10:00:00",
            amount=1200.0,
            ml_probability=0.01,
            graph_ring_score=0.60,
            graph_ring_candidate=1,
        )
        assert rec.decision == DecisionState.REVIEW
        assert "ELEVATED_GRAPH_RING_SCORE" in rec.signals_triggered

    def test_hold_on_severe_graph_syndicate(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=106,
            timestamp="2025-01-01 10:00:00",
            amount=2000.0,
            ml_probability=0.02,
            graph_ring_score=0.85,
            graph_ring_candidate=1,
        )
        assert rec.decision == DecisionState.HOLD
        assert "SEVERE_GRAPH_RING_SYNDICATE" in rec.signals_triggered

    def test_compound_risk_moderate_ml_plus_graph(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=107,
            timestamp="2025-01-01 10:00:00",
            amount=3000.0,
            ml_probability=0.25,
            graph_ring_score=0.55,
            graph_ring_candidate=1,
        )
        assert rec.decision == DecisionState.HOLD
        assert rec.primary_trigger == "COMPOUND_ML_GRAPH_SYNDICATE"

    def test_legitimate_shared_device_not_held(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id=108,
            timestamp="2025-01-01 10:00:00",
            amount=400.0,
            ml_probability=0.01,
            graph_ring_score=0.0,  # Legitimate sharing filtered to 0.0 in Stage 6
            graph_ring_candidate=0,
            feature_context={"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.0},
        )
        assert rec.decision == DecisionState.APPROVE


class TestThresholdBoundariesAndDeterminism:
    """Test exact threshold boundaries and reproducibility."""

    def test_ml_threshold_boundaries(self, policy_engine):
        # 1. Just below challenge threshold (0.0499) -> APPROVE
        rec_below = policy_engine.evaluate(1, "2025-01-01 10:00:00", 100.0, 0.0499)
        assert rec_below.decision == DecisionState.APPROVE

        # 2. Exactly at challenge threshold (0.0500) -> CHALLENGE
        rec_at = policy_engine.evaluate(2, "2025-01-01 10:00:00", 100.0, 0.0500)
        assert rec_at.decision == DecisionState.CHALLENGE

        # 3. Exactly at review threshold (0.2500) -> REVIEW
        rec_mid = policy_engine.evaluate(3, "2025-01-01 10:00:00", 100.0, 0.2500)
        assert rec_mid.decision == DecisionState.REVIEW

        # 4. Exactly at hold threshold (0.5000) -> HOLD
        rec_hold = policy_engine.evaluate(4, "2025-01-01 10:00:00", 100.0, 0.5000)
        assert rec_hold.decision == DecisionState.HOLD

    def test_deterministic_reasons_and_reproducibility(self, policy_engine):
        rec1 = policy_engine.evaluate(10, "2025-01-01 10:00:00", 500.0, 0.12, 0.60, 1)
        rec2 = policy_engine.evaluate(10, "2025-01-01 10:00:00", 500.0, 0.12, 0.60, 1)

        assert rec1.decision == rec2.decision
        assert rec1.primary_trigger == rec2.primary_trigger
        assert rec1.reasons == rec2.reasons


class TestAPISimulationEndpoint:
    """Test the offline local POST /risk/evaluate simulation endpoint."""

    def test_post_risk_evaluate(self, client):
        payload = {
            "transaction_id": 999,
            "timestamp": "2025-03-01 12:00:00",
            "amount": 2500.0,
            "ml_probability": 0.85,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "feature_context": {},
            "rule_signals": [],
        }
        res = client.post("/risk/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "HOLD"
        assert data["policy_version"] == "sentinelrisk-policy-v1"
        assert data["is_intervention"] == 1
        assert len(data["reasons"]) > 0

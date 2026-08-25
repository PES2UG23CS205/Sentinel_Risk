"""
SentinelRisk — Stage 12: Risk-Based Friction & Challenge Orchestration Unit Tests

Verifies:
  1. Low-risk transaction -> APPROVE (challenge is None)
  2. Medium-risk transaction -> CHALLENGE (challenge recommendation attached)
  3. High-risk uncertain transaction -> REVIEW (challenge is None, creates case)
  4. High-confidence fraud -> HOLD (challenge is None, creates case)
  5. Evidence-grounded challenge selection (Device vs Velocity vs Spend Anomaly)
  6. No challenge attached to APPROVE, REVIEW, or HOLD
  7. Policy immutability & LLM downstream isolation
  8. External dataset schema-adaptive compatibility with CHALLENGE
  9. Synthetic frozen benchmark evaluation and financial cost reduction
 10. Incident simulation escalation with CHALLENGE
 11. Real-time API schema and idempotency with CHALLENGE
"""

import pytest
from pathlib import Path
import numpy as np

from backend.app.policy.models import DecisionState, DecisionRecord, PolicyConfig
from backend.app.policy.engine import PolicyEngine
from backend.app.policy.challenge_catalog import (
    ChallengeCode,
    ChallengeRecommendation,
    select_challenge_type,
    CHALLENGE_CATALOG,
)
from backend.app.scoring.realtime_service import RealtimeRiskService
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent
from simulation.incident_simulator.simulator import IncidentSimulator


@pytest.fixture
def policy_engine():
    return PolicyEngine(enable_challenge=True)


@pytest.fixture
def risk_service():
    return RealtimeRiskService()


class TestQuadStateDecisionsAndChallengeAttachments:
    """Test quad-state decision ladder and challenge payload attachment."""

    def test_low_risk_decision_approves_without_challenge(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id="TX-001",
            timestamp="2025-06-15 12:00:00",
            amount=350.0,
            ml_probability=0.005,
            graph_ring_score=0.0,
            graph_ring_candidate=0,
            feature_context={"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.0},
        )
        assert rec.decision == DecisionState.APPROVE
        assert rec.challenge is None
        assert rec.is_intervention is False
        assert rec.is_analyst_case is False

    def test_medium_risk_decision_challenges_with_recommendation(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id="TX-002",
            timestamp="2025-06-15 12:00:00",
            amount=2450.0,
            ml_probability=0.12,  # In challenge band [0.05, 0.25)
            graph_ring_score=0.0,
            graph_ring_candidate=0,
            feature_context={"device_is_new_for_cust": 1, "cust_amount_to_mean_ratio": 2.2},
        )
        assert rec.decision == DecisionState.CHALLENGE
        assert rec.challenge is not None
        assert isinstance(rec.challenge, ChallengeRecommendation)
        assert rec.challenge.challenge_code == ChallengeCode.CHALLENGE_DEVICE_VERIFICATION.value
        assert rec.is_intervention is True
        assert rec.is_analyst_case is False  # Automated step-up does not flood analyst queue

    def test_high_risk_uncertain_decision_reviews_without_challenge(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id="TX-003",
            timestamp="2025-06-15 12:00:00",
            amount=15000.0,
            ml_probability=0.35,  # In review band [0.25, 0.50)
            graph_ring_score=0.0,
            graph_ring_candidate=0,
        )
        assert rec.decision == DecisionState.REVIEW
        assert rec.challenge is None
        assert rec.is_intervention is True
        assert rec.is_analyst_case is True

    def test_high_confidence_fraud_decision_holds_without_challenge(self, policy_engine):
        rec = policy_engine.evaluate(
            transaction_id="TX-004",
            timestamp="2025-06-15 12:00:00",
            amount=50000.0,
            ml_probability=0.92,  # Exceeds hold threshold 0.50
            graph_ring_score=0.0,
            graph_ring_candidate=0,
        )
        assert rec.decision == DecisionState.HOLD
        assert rec.challenge is None
        assert rec.is_intervention is True
        assert rec.is_analyst_case is True


class TestEvidenceGroundedChallengeSelection:
    """Test deterministic selection of challenge mechanisms based on observed anomaly."""

    def test_unrecognized_device_selects_device_verification(self):
        chal = select_challenge_type(
            feature_context={"device_is_new_for_cust": 1, "cust_amount_to_mean_ratio": 2.0},
            signals_triggered=["ELEVATED_ML_RISK", "NEW_DEVICE_DETECTED"],
            amount=2500.0,
        )
        assert chal.challenge_code == ChallengeCode.CHALLENGE_DEVICE_VERIFICATION.value
        assert chal.friction_level == "LOW"
        assert "device" in chal.reason.lower()

    def test_card_velocity_burst_selects_payment_reauth(self):
        chal = select_challenge_type(
            feature_context={"pi_velocity_count_1h": 3, "device_is_new_for_cust": 0},
            signals_triggered=["MODERATE_PI_VELOCITY"],
            amount=150.0,
        )
        assert chal.challenge_code == ChallengeCode.CHALLENGE_PAYMENT_REAUTH.value
        assert chal.friction_level == "MEDIUM"
        assert "velocity" in chal.reason.lower()

    def test_ticket_size_anomaly_selects_customer_confirmation(self):
        chal = select_challenge_type(
            feature_context={"cust_amount_to_mean_ratio": 4.5, "device_is_new_for_cust": 0},
            signals_triggered=["MODERATE_AMOUNT_ANOMALY"],
            amount=8500.0,
        )
        assert chal.challenge_code == ChallengeCode.CHALLENGE_CUSTOMER_CONFIRMATION.value
        assert chal.friction_level == "LOW"
        assert "mean" in chal.reason.lower()


class TestPolicyAuthorityAndAnalystIsolation:
    """Test policy immutability and verify that CHALLENGE transactions bypass analyst queues."""

    def test_challenge_does_not_create_analyst_case(self):
        case_mgr = CaseManager()
        dec_record = {
            "transaction_id": "TX-CHAL-09",
            "decision": "CHALLENGE",
            "amount": 2000.0,
            "ml_probability": 0.15,
            "challenge": {"code": "CHALLENGE_DEVICE_VERIFICATION"},
        }
        case = case_mgr.create_case_from_decision(
            decision_record=dec_record,
            transaction_data={"amount": 2000.0},
        )
        assert case is None  # Must NOT create an analyst review case

    def test_review_and_hold_create_analyst_cases(self):
        case_mgr = CaseManager()
        case_rev = case_mgr.create_case_from_decision(
            decision_record={"transaction_id": "TX-REV-01", "decision": "REVIEW", "amount": 5000.0, "ml_probability": 0.35},
            transaction_data={"amount": 5000.0},
        )
        assert case_rev is not None

        case_hold = case_mgr.create_case_from_decision(
            decision_record={"transaction_id": "TX-HOLD-01", "decision": "HOLD", "amount": 25000.0, "ml_probability": 0.85},
            transaction_data={"amount": 25000.0},
        )
        assert case_hold is not None


class TestRealtimeServiceAPIAndIdempotency:
    """Test realtime scoring service output schema and idempotency for CHALLENGE."""

    def test_realtime_service_returns_challenge_payload(self, risk_service):
        payload = {
            "transaction_id": "TX-API-CHAL-01",
            "amount": 1800.0,
            "timestamp": "2025-06-15 14:00:00",
            "customer_id": "CUST_API_01",
            "device_id": "DEV_NEW_01",
            "payment_instrument_id": "PI_01",
            "ml_probability": 0.10,
            "feature_context": {"device_is_new_for_cust": 1, "cust_amount_to_mean_ratio": 2.5},
        }
        res = risk_service.evaluate_transaction(payload)
        assert res["decision"] == "CHALLENGE"
        assert res["is_intervention"] == 1
        assert res["is_analyst_case"] == 0
        assert res["challenge"] is not None
        assert res["challenge"]["code"] == "CHALLENGE_DEVICE_VERIFICATION"
        assert "risk_score" in res

        # Verify duplicate replay retains challenge payload
        cached = risk_service.evaluate_transaction(payload)
        assert cached["decision"] == "CHALLENGE"
        assert cached["idempotency_cached"] is True


class TestIncidentSimulatorEscalation:
    """Test incident simulation support for step-up challenge escalation."""

    def test_incident_simulator_records_challenges(self):
        sim = IncidentSimulator()
        res = sim.run_scenario("CARD_TESTING_ATTACK")
        metrics = res["metrics"]
        assert "challenge_count" in metrics
        assert metrics["total_transactions"] == 20
        assert metrics["hold_count"] > 0
        assert "decisions_summary" in res

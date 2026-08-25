"""
SentinelRisk — Final End-to-End Integration & Decision Immutability Tests

Verifies complete execution across all layers:
  Transaction -> Features -> ML -> Graph -> Rules -> Policy -> Decision -> Case -> Investigation -> Report
"""

import pytest
from backend.app.scoring.realtime_service import RealtimeRiskService
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.agent import InvestigationAgent
from backend.app.investigation.models import CaseStatus, CasePriority
from simulation.incident_simulator.simulator import IncidentSimulator


@pytest.fixture
def risk_service():
    return RealtimeRiskService()


@pytest.fixture
def investigation_agent():
    return InvestigationAgent()


@pytest.fixture
def case_manager(investigation_agent):
    return CaseManager(investigation_agent)


class TestEndToEndRiskPipeline:
    """End-to-end evaluation across all four primary transaction types."""

    def test_e2e_legitimate_transaction(self, risk_service, case_manager):
        payload = {
            "transaction_id": "E2E-LEGIT-001",
            "customer_id": "CUST_LEGIT_1",
            "device_id": "DEV_LEGIT_1",
            "payment_instrument_id": "PI_LEGIT_1",
            "merchant_id": "MERCH_1",
            "amount": 350.00,
            "timestamp": "2025-06-15 14:00:00",
            "ml_probability": 0.001,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.0, "device_is_new_for_cust": 0},
        }

        res = risk_service.evaluate_transaction(payload)
        assert res["decision"] == "APPROVE"
        assert res["is_intervention"] == 0

        # Verify no case created for APPROVE
        case = case_manager.create_case_from_decision(res, payload)
        assert case is None

    def test_e2e_account_takeover(self, risk_service, case_manager):
        payload = {
            "transaction_id": "E2E-ATO-002",
            "customer_id": "CUST_VICTIM_2",
            "device_id": "DEV_ATTACKER_2",
            "payment_instrument_id": "PI_VICTIM_2",
            "merchant_id": "MERCH_2",
            "amount": 28000.00,
            "timestamp": "2025-06-15 02:15:00",
            "ml_probability": 0.985,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 7.0, "cust_amount_zscore": 4.5, "device_is_new_for_cust": 1},
        }

        # 1. Authoritative Decision
        res = risk_service.evaluate_transaction(payload)
        assert res["decision"] == "HOLD"
        assert res["is_intervention"] == 1

        # 2. Case Management
        case = case_manager.create_case_from_decision(res, payload)
        assert case is not None
        assert case.priority == CasePriority.CRITICAL

        # 3. Investigation
        report = case_manager.investigate_case(case.case_id)
        assert report.case_id == case.case_id
        assert report.policy_decision == "HOLD"
        assert len(report.findings) > 0
        assert "Account Takeover" in report.hypotheses[0].hypothesis

    def test_e2e_coordinated_abuse_ring(self, risk_service, case_manager):
        payload = {
            "transaction_id": "E2E-RING-003",
            "customer_id": "CUST_RING_3",
            "device_id": "DEV_RING_SHARED",
            "payment_instrument_id": "PI_RING_SHARED",
            "merchant_id": "MERCH_3",
            "amount": 3400.00,
            "timestamp": "2025-06-15 04:30:00",
            "ml_probability": 0.22,
            "graph_ring_score": 0.88,
            "graph_ring_candidate": 1,
            "features": {"pi_velocity_count_1h": 2, "cust_amount_to_mean_ratio": 1.2, "device_customer_count": 6, "payment_instrument_customer_count": 5},
        }

        res = risk_service.evaluate_transaction(payload)
        assert res["decision"] == "HOLD"

        case = case_manager.create_case_from_decision(res, payload, {"graph_ring_score": 0.88, "graph_ring_candidate": 1})
        report = case_manager.investigate_case(case.case_id)
        assert any("ring score" in f.statement.lower() for f in report.findings)

    def test_e2e_card_testing(self, risk_service, case_manager):
        payload = {
            "transaction_id": "E2E-BOT-004",
            "customer_id": "CUST_BOT_4",
            "device_id": "DEV_BOT_4",
            "payment_instrument_id": "PI_STOLEN_4",
            "merchant_id": "MERCH_4",
            "amount": 75.00,
            "timestamp": "2025-06-15 02:05:00",
            "ml_probability": 0.999,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 8, "velocity_txn_count_1h": 8, "device_is_new_for_cust": 1},
        }

        res = risk_service.evaluate_transaction(payload)
        assert res["decision"] == "HOLD"

        case = case_manager.create_case_from_decision(res, payload)
        report = case_manager.investigate_case(case.case_id)
        assert any("velocity" in f.statement.lower() for f in report.findings)


class TestDecisionImmutability:
    """Verify that AI Investigation Agent cannot override or modify policy decisions."""

    def test_policy_decision_immutability_under_uncertain_investigation(self, risk_service, case_manager):
        payload = {
            "transaction_id": "E2E-IMMUTABLE-001",
            "customer_id": "CUST_TEST",
            "device_id": "DEV_TEST",
            "payment_instrument_id": "PI_TEST",
            "merchant_id": "MERCH_TEST",
            "amount": 15000.00,
            "timestamp": "2025-06-15 10:00:00",
            "ml_probability": 0.96,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 5.0, "device_is_new_for_cust": 1},
        }

        res = risk_service.evaluate_transaction(payload)
        assert res["decision"] == "HOLD"

        case = case_manager.create_case_from_decision(res, payload)
        report = case_manager.investigate_case(case.case_id)

        # Authoritative decision must remain HOLD despite any investigation text
        assert res["decision"] == "HOLD"
        assert report.policy_decision == "HOLD"
        assert case.policy_decision == "HOLD"


class TestIncidentSimulatorEndToEnd:
    """Verify end-to-end incident simulation execution."""

    def test_2am_incident_simulation(self):
        sim = IncidentSimulator()
        res = sim.run_scenario("CARD_TESTING_ATTACK")
        assert res["metrics"]["total_transactions"] == 20
        assert res["metrics"]["hold_count"] >= 15
        assert len(res["recovery_recommendations"]) >= 2

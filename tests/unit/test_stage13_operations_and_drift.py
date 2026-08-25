"""
Tests for Stage 13: Fraud Operations Center & Model/Feature Drift Monitoring
"""

import pytest
import numpy as np
from backend.app.investigation.case_manager import CaseManager
from backend.app.investigation.models import CaseStatus, CasePriority
from backend.app.investigation.agent import InvestigationAgent
from ml.monitoring.drift_detector import calculate_psi, ModelDriftMonitor


def test_case_priority_deterministic_assignment():
    mgr = CaseManager(InvestigationAgent())
    
    # Critical: HOLD with high ML & Ring
    c_crit = mgr.create_case_from_decision(
        decision_record={"decision": "HOLD", "ml_probability": 0.95, "graph_ring_score": 0.85, "amount": 2500.0},
        transaction_data={"transaction_id": "TXN_C1", "amount": 2500.0},
    )
    assert c_crit.priority == CasePriority.CRITICAL
    assert "Severe compound threat" in c_crit.priority_reason

    # High: REVIEW with ring anomaly
    c_high = mgr.create_case_from_decision(
        decision_record={"decision": "REVIEW", "ml_probability": 0.15, "graph_ring_score": 0.65, "amount": 1200.0},
        transaction_data={"transaction_id": "TXN_C2", "amount": 1200.0},
    )
    assert c_high.priority == CasePriority.HIGH


def test_case_lifecycle_and_analyst_feedback():
    mgr = CaseManager(InvestigationAgent())
    case = mgr.create_case_from_decision(
        decision_record={"decision": "HOLD", "ml_probability": 0.88, "graph_ring_score": 0.0, "amount": 15000.0},
        transaction_data={"transaction_id": "TXN_C3", "amount": 15000.0},
    )
    assert case.status == CaseStatus.OPEN
    assert case.assigned_to is None

    # Assign
    mgr.assign_case(case.case_id, analyst="Risk_Analyst_Priya")
    assert case.assigned_to == "Risk_Analyst_Priya"
    assert case.status == CaseStatus.INVESTIGATING

    # Add Note
    mgr.add_note(case.case_id, analyst="Risk_Analyst_Priya", text="Verified with issuer; card is stolen.")
    assert len(case.notes) == 1

    # Confirm Fraud Feedback
    mgr.confirm_fraud(case.case_id, analyst="Risk_Analyst_Priya", notes="Confirmed ATO.")
    assert case.status == CaseStatus.RESOLVED
    assert case.resolution == "CONFIRMED_FRAUD"

    # Verify Feedback Metrics
    metrics = mgr.get_feedback_metrics()
    assert metrics["confirmed_fraud_count"] >= 1
    assert metrics["analyst_confirmation_rate_pct"] > 0.0


def test_population_stability_index_computation():
    # Identical distributions should have PSI close to 0
    rng = np.random.default_rng(42)
    expected = rng.normal(loc=100.0, scale=15.0, size=1000)
    actual_same = rng.normal(loc=100.0, scale=15.0, size=1000)
    psi_same = calculate_psi(expected, actual_same, bins=10)
    assert psi_same < 0.10, f"Expected normal PSI < 0.10, got {psi_same}"

    # Shifted distribution should produce high PSI
    actual_shifted = rng.normal(loc=150.0, scale=30.0, size=1000)
    psi_shifted = calculate_psi(expected, actual_shifted, bins=10)
    assert psi_shifted > 0.25, f"Expected drift PSI > 0.25, got {psi_shifted}"


def test_model_drift_monitor_report():
    monitor = ModelDriftMonitor()
    sample_events = [
        {"transaction_id": "T1", "amount": 500.0, "decision": "APPROVE", "features": {"cust_velocity_1h": 1, "cust_amount_ratio": 1.0}},
        {"transaction_id": "T2", "amount": 3500.0, "decision": "CHALLENGE", "features": {"cust_velocity_1h": 1, "cust_amount_ratio": 2.5}},
        {"transaction_id": "T3", "amount": 45000.0, "decision": "HOLD", "features": {"cust_velocity_1h": 8, "cust_amount_ratio": 8.0}},
    ]
    report = monitor.evaluate_drift(sample_events)
    assert "model_metadata" in report
    assert "monitored_features" in report
    assert len(report["monitored_features"]) >= 4
    assert "operational_distributions" in report
    assert report["operational_distributions"]["current_sample_size"] == 3

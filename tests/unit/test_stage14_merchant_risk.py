"""
Tests for Stage 14: Merchant Risk Intelligence, Scoring, and Alerts
"""

import pytest
import pandas as pd
from backend.app.merchant.risk_profiler import MerchantRiskProfiler
from backend.app.merchant.risk_scorer import MerchantRiskScorer
from backend.app.merchant.alerts import MerchantAlertGenerator


def test_merchant_profiler_aggregations():
    txns = [
        {"transaction_id": "T1", "merchant_id": "M_TEST", "merchant_category": "Gaming", "amount": 100.0, "is_fraud": 0, "decision": "APPROVE", "timestamp": "2025-06-15 10:00:00", "customer_id": "C1"},
        {"transaction_id": "T2", "merchant_id": "M_TEST", "merchant_category": "Gaming", "amount": 200.0, "is_fraud": 0, "decision": "APPROVE", "timestamp": "2025-06-15 10:30:00", "customer_id": "C2"},
        {"transaction_id": "T3", "merchant_id": "M_TEST", "merchant_category": "Gaming", "amount": 300.0, "is_fraud": 1, "decision": "HOLD", "timestamp": "2025-06-15 11:00:00", "customer_id": "C1"},
    ]
    profiler = MerchantRiskProfiler(txns)
    prof = profiler.profile_merchant("M_TEST")

    assert prof["merchant_id"] == "M_TEST"
    assert prof["total_transactions"] == 3
    assert prof["total_volume_inr"] == 600.0
    assert prof["fraud_count"] == 1
    assert abs(prof["fraud_rate_pct"] - 33.33) < 0.1
    assert prof["merchant_category"] == "Gaming"


def test_merchant_risk_scorer_and_driver_attribution():
    scorer = MerchantRiskScorer()
    sample_prof = {
        "merchant_id": "M_HIGH_RISK",
        "fraud_rate_pct": 5.0,
        "window_metrics": {"1h_transactions": 20},
        "review_rate_pct": 3.0,
        "hold_rate_pct": 3.0,
        "customer_concentration_pct": 55.0,
        "trend_direction": "DETERIORATING",
    }
    score_res = scorer.score_merchant(sample_prof)

    assert score_res["risk_level"] == "HIGH"
    assert score_res["risk_score"] >= 0.60
    assert "drivers" in score_res
    assert score_res["drivers"]["fraud_rate_contribution"] > 0
    assert score_res["drivers"]["velocity_anomaly_contribution"] > 0
    assert len(score_res["driver_explanations"]) == 5


def test_merchant_alert_generation():
    alert_gen = MerchantAlertGenerator()
    sample_prof = {
        "merchant_id": "M_ALERT_TEST",
        "fraud_rate_pct": 4.5,
        "window_metrics": {"1h_transactions": 22},
        "customer_concentration_pct": 60.0,
        "trend_direction": "DETERIORATING",
        "review_rate_pct": 4.0,
        "hold_rate_pct": 2.0,
        "total_transactions": 50,
        "as_of_timestamp": "2025-06-15 12:00:00",
    }
    score_data = {"risk_score": 0.85, "risk_level": "HIGH"}
    alerts = alert_gen.generate_alerts(sample_prof, score_data)

    alert_types = [a["alert_type"] for a in alerts]
    assert "FRAUD_RATE_SPIKE" in alert_types
    assert "VELOCITY_SPIKE" in alert_types
    assert "RISK_SCORE_INCREASE" in alert_types
    assert "UNUSUAL_CUSTOMER_CONCENTRATION" in alert_types

    # Ensure analyst authority retained (action recommendations)
    for a in alerts:
        assert a["recommended_action"] in ("MONITOR", "REVIEW", "ESCALATE")

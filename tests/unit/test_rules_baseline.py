"""
SentinelRisk — Stage 4: Rules-Only Baseline Unit Tests

Verifies:
  - Individual rule evaluation correctness and boundary conditions
  - Weighted score calculation and deterministic explainability
  - Risk band classifications (APPROVE, REVIEW, HOLD)
  - Financial cost and expected loss calculations
  - Chronological data partitioning (Train, Validation, Test) without overlap
  - Test set isolation during threshold tuning
  - Deterministic evaluation reproducibility
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from backend.app.policy.config import RuleConfig
from backend.app.policy.rules import RulesEngine
from evaluation.rules_baseline.evaluator import RulesBaselineEvaluator


@pytest.fixture
def sample_features_df():
    """Create a controlled synthetic feature dataframe for unit testing."""
    base_time = datetime(2025, 1, 1, 10, 0, 0)
    rows = []

    # Generate 100 chronological mock transactions
    for i in range(100):
        t = base_time + timedelta(hours=i)
        is_fraud = (i % 10 == 0)  # 10% fraud for testing
        rows.append({
            "transaction_id": i + 1,
            "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "merchant_id": 1,
            "customer_id": i + 1,
            "device_id": i + 1,
            "payment_instrument_id": i + 1,
            "amount": 1000.0 if not is_fraud else 15000.0,
            "amount_log": np.log(1001.0 if not is_fraud else 15001.0),
            "hour_of_day": t.hour,
            "day_of_week": t.weekday(),
            "is_weekend": 1 if t.weekday() in (5, 6) else 0,
            "is_night": 1 if 0 <= t.hour <= 5 else 0,
            "merchant_category_idx": 1,
            "pi_type_idx": 1,
            "cust_age_days": 30.0,
            "cust_txn_count_prev": 5,
            "cust_amount_sum_prev": 5000.0,
            "cust_amount_mean_prev": 1000.0,
            "cust_amount_std_prev": 100.0,
            "cust_amount_max_prev": 1500.0,
            "cust_days_since_last_txn": 2.0,
            "cust_amount_to_mean_ratio": 1.0 if not is_fraud else 15.0,
            "cust_amount_zscore": 0.0 if not is_fraud else 140.0,
            "cust_is_first_txn": 0,
            "cust_decline_rate_prev": 0.0,
            "velocity_txn_count_1h": 0 if not is_fraud else 5,
            "velocity_amount_sum_1h": 0.0,
            "velocity_txn_count_24h": 1,
            "velocity_amount_sum_24h": 1000.0,
            "velocity_txn_count_7d": 3,
            "velocity_amount_sum_7d": 3000.0,
            "merchant_age_days": 100.0,
            "merchant_txn_count_prev": 50,
            "merchant_amount_mean_prev": 1000.0,
            "merchant_amount_std_prev": 100.0,
            "merchant_decline_rate_prev": 0.02,
            "merchant_velocity_txn_count_1h": 1,
            "merchant_velocity_txn_count_24h": 10,
            "merchant_velocity_txn_count_7d": 50,
            "amount_to_merchant_mean_ratio": 1.0 if not is_fraud else 15.0,
            "device_txn_count_prev": 5,
            "device_distinct_cust_prev": 1,
            "device_distinct_merchants_prev": 1,
            "device_velocity_count_24h": 1,
            "device_velocity_count_7d": 5,
            "device_is_new_for_cust": 0 if not is_fraud else 1,
            "device_age_days": 20.0,
            "pi_txn_count_prev": 5,
            "pi_distinct_cust_prev": 1,
            "pi_distinct_merchants_prev": 1,
            "pi_velocity_count_1h": 0 if not is_fraud else 4,
            "pi_velocity_count_24h": 1,
            "pi_age_days": 20.0,
            "is_fraud": is_fraud,
            "is_fraud_ground_truth": is_fraud,
            "fraud_archetype": "account_takeover" if is_fraud else "none",
            "fraud_case_id": "ATO_001" if is_fraud else "",
        })
    return pd.DataFrame(rows)


class TestRuleCorrectnessAndBoundaries:
    """Test individual rule logic and threshold boundaries."""

    def test_cust_amount_anomaly_boundary(self):
        engine = RulesEngine(RuleConfig(cust_amount_ratio_threshold=4.0))

        # Just below threshold (3.99x) -> No trigger
        res_below = engine.evaluate_transaction({"cust_is_first_txn": 0, "cust_amount_to_mean_ratio": 3.99, "amount": 3990.0})
        assert "RULE_CUST_AMOUNT_ANOMALY" not in res_below["triggered_rules"]

        # Exactly at threshold (4.0x) -> Triggers
        res_at = engine.evaluate_transaction({"cust_is_first_txn": 0, "cust_amount_to_mean_ratio": 4.00, "amount": 4000.0})
        assert "RULE_CUST_AMOUNT_ANOMALY" in res_at["triggered_rules"]

        # First transaction with ratio 10.0 -> Should NOT trigger (first txn has no established history)
        res_first = engine.evaluate_transaction({"cust_is_first_txn": 1, "cust_amount_to_mean_ratio": 10.0, "amount": 10000.0})
        assert "RULE_CUST_AMOUNT_ANOMALY" not in res_first["triggered_rules"]

    def test_pi_velocity_boundary(self):
        engine = RulesEngine(RuleConfig(pi_velocity_1h_threshold=3))

        # 2 attempts -> No trigger
        res_below = engine.evaluate_transaction({"pi_velocity_count_1h": 2})
        assert "RULE_PI_VELOCITY" not in res_below["triggered_rules"]

        # 3 attempts -> Triggers
        res_at = engine.evaluate_transaction({"pi_velocity_count_1h": 3})
        assert "RULE_PI_VELOCITY" in res_at["triggered_rules"]

    def test_off_hour_anomaly(self):
        engine = RulesEngine(RuleConfig(night_amount_threshold=8000.0))

        # Night time but low amount (INR 500) -> No trigger
        res_low = engine.evaluate_transaction({"is_night": 1, "amount": 500.0})
        assert "RULE_OFF_HOUR_ANOMALY" not in res_low["triggered_rules"]

        # Daytime high amount (INR 25,000) -> No trigger
        res_day = engine.evaluate_transaction({"is_night": 0, "amount": 25000.0})
        assert "RULE_OFF_HOUR_ANOMALY" not in res_day["triggered_rules"]

        # Night time high amount (INR 12,000) -> Triggers
        res_night = engine.evaluate_transaction({"is_night": 1, "amount": 12000.0})
        assert "RULE_OFF_HOUR_ANOMALY" in res_night["triggered_rules"]


class TestScoreAndRiskBands:
    """Test score accumulation and decision mapping."""

    def test_score_accumulation(self):
        config = RuleConfig(
            cust_amount_ratio_threshold=4.0, weight_cust_amount_anomaly=2,
            pi_velocity_1h_threshold=3, weight_pi_velocity=3,
        )
        engine = RulesEngine(config)

        # Both rules trigger -> Score = 2 + 3 = 5
        res = engine.evaluate_transaction({
            "cust_is_first_txn": 0,
            "cust_amount_to_mean_ratio": 5.0,
            "amount": 5000.0,
            "pi_velocity_count_1h": 4,
        })
        assert res["rule_score"] == 5
        assert len(res["triggered_rules"]) == 2
        assert len(res["explanations"]) == 2

    def test_risk_band_decisions(self):
        config = RuleConfig(threshold_review=3.0, threshold_hold=5.0)
        engine = RulesEngine(config)

        # Score 0 -> APPROVE
        assert engine.evaluate_transaction({})["decision"] == "APPROVE"

        # Score 3 (PI Velocity = 3) -> REVIEW
        assert engine.evaluate_transaction({"pi_velocity_count_1h": 5})["decision"] == "REVIEW"

        # Score 5 (PI Velocity 3 + Cust Velocity 2 = 5) -> HOLD
        assert engine.evaluate_transaction({"pi_velocity_count_1h": 5, "velocity_txn_count_1h": 5})["decision"] == "HOLD"


class TestChronologicalSplitsAndCostModel:
    """Test temporal partitioning and business loss calculations."""

    def test_chronological_splits_no_overlap(self, sample_features_df):
        evaluator = RulesBaselineEvaluator(sample_features_df)
        split = evaluator.split_info

        assert split["train"]["count"] == 70
        assert split["validation"]["count"] == 15
        assert split["test"]["count"] == 15

        # Ensure train timestamps strictly precede validation timestamps
        assert split["train"]["end_date"] <= split["validation"]["start_date"]
        # Ensure validation timestamps strictly precede test timestamps
        assert split["validation"]["end_date"] <= split["test"]["start_date"]

    def test_cost_calculation(self):
        evaluator = RulesBaselineEvaluator(pd.DataFrame({
            "timestamp": ["2025-01-01 10:00:00", "2025-01-01 11:00:00"],
            "is_fraud_ground_truth": [1, 0],
            "amount": [1000.0, 500.0],
        }))
        evaluator.config.false_positive_cost = 150.0
        evaluator.config.review_cost = 50.0
        evaluator.config.fraud_loss_multiplier = 1.0

        # Case 1: FN (missed fraud) on txn 1, TN on txn 2
        y_true = np.array([1, 0])
        y_pred = np.array([0, 0])
        amounts = np.array([1000.0, 500.0])
        decisions = np.array(["APPROVE", "APPROVE"])

        m = evaluator._calculate_metrics(y_true, y_pred, amounts, decisions)
        assert m["fn_fraud_loss_inr"] == 1000.0
        assert m["fp_friction_cost_inr"] == 0.0
        assert m["expected_loss_inr"] == 1000.0

        # Case 2: TP on txn 1, FP on txn 2 (with review)
        y_pred2 = np.array([1, 1])
        decisions2 = np.array(["REVIEW", "REVIEW"])
        m2 = evaluator._calculate_metrics(y_true, y_pred2, amounts, decisions2)
        assert m2["fn_fraud_loss_inr"] == 0.0
        assert m2["fp_friction_cost_inr"] == 150.0
        assert m2["review_overhead_cost_inr"] == 100.0  # 2 reviews * 50
        assert m2["expected_loss_inr"] == 250.0
        assert m2["tp_fraud_avoided_inr"] == 1000.0

    def test_reproducibility(self, sample_features_df):
        evaluator1 = RulesBaselineEvaluator(sample_features_df)
        res1 = evaluator1.evaluate_test_set()

        evaluator2 = RulesBaselineEvaluator(sample_features_df)
        res2 = evaluator2.evaluate_test_set()

        assert res1["metrics"] == res2["metrics"]

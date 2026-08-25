"""
SentinelRisk — Point-in-Time Feature Engineering Unit Tests

Verifies:
  - Strict point-in-time calculation (current transaction excluded, no future lookahead)
  - Accurate rolling velocity windows (1h, 24h, 7d) and boundary conditions
  - Cold-start handling for new customers, merchants, devices, and payment instruments
  - Numerical stability (no NaNs, Infs, or divide-by-zero errors)
  - Deterministic reproducibility
  - Automated leakage checks and deliberate leakage rejection
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ml.features.config import FeatureConfig
from ml.features.feature_pipeline import FeaturePipeline
from ml.features.leakage_checks import LeakageChecker, run_deliberate_leakage_test
from ml.features.customer_features import CustomerHistoryState
from ml.features.velocity_features import CustomerVelocityState
from ml.features.merchant_features import MerchantHistoryState
from ml.features.device_features import DeviceHistoryState
from ml.features.payment_instrument_features import PaymentInstrumentHistoryState


@pytest.fixture
def mock_dataset():
    """Create a controlled mini-dataset with known timestamps and values for exact unit tests."""
    base_time = datetime(2025, 1, 1, 10, 0, 0)

    merchants = [
        {"id": 1, "name": "Shop_A", "category": "electronics", "created_at": base_time - timedelta(days=30), "typical_order_value": 5000.0, "tier": "medium"},
        {"id": 2, "name": "Shop_B", "category": "grocery", "created_at": base_time - timedelta(days=10), "typical_order_value": 500.0, "tier": "small"},
    ]

    customers = [
        {"id": 1, "segment": "regular", "account_created_at": base_time - timedelta(days=20), "typical_amount": 2000.0, "txn_per_month": 4.0},
        {"id": 2, "segment": "new", "account_created_at": base_time, "typical_amount": 1000.0, "txn_per_month": 1.0},
    ]

    devices = [
        {"id": 1, "created_at": base_time - timedelta(days=20)},
        {"id": 2, "created_at": base_time},
    ]

    payment_instruments = [
        {"id": 1, "customer_id": 1, "type": "card", "created_at": base_time - timedelta(days=20)},
        {"id": 2, "customer_id": 2, "type": "upi", "created_at": base_time},
    ]

    # Chronological sequence of transactions
    transactions = [
        # Customer 1 - Txn 1 at 10:00 AM
        {
            "id": 1, "merchant_id": 1, "customer_id": 1, "device_id": 1, "payment_instrument_id": 1,
            "amount": 1000.0, "currency": "INR", "timestamp": base_time, "status": "captured",
            "is_fraud": False, "is_fraud_ground_truth": False, "fraud_archetype": "none", "fraud_case_id": None
        },
        # Customer 1 - Txn 2 at 10:30 AM (30 min later, inside 1h window)
        {
            "id": 2, "merchant_id": 1, "customer_id": 1, "device_id": 1, "payment_instrument_id": 1,
            "amount": 2000.0, "currency": "INR", "timestamp": base_time + timedelta(minutes=30), "status": "captured",
            "is_fraud": False, "is_fraud_ground_truth": False, "fraud_archetype": "none", "fraud_case_id": None
        },
        # Customer 1 - Txn 3 at 11:15 AM (75 min after Txn 1 -> Txn 1 outside 1h, Txn 2 inside 1h)
        {
            "id": 3, "merchant_id": 1, "customer_id": 1, "device_id": 2, "payment_instrument_id": 1,
            "amount": 3000.0, "currency": "INR", "timestamp": base_time + timedelta(minutes=75), "status": "captured",
            "is_fraud": True, "is_fraud_ground_truth": True, "fraud_archetype": "account_takeover", "fraud_case_id": "ATO_001"
        },
        # Customer 2 - Cold start Txn at 12:00 PM
        {
            "id": 4, "merchant_id": 2, "customer_id": 2, "device_id": 2, "payment_instrument_id": 2,
            "amount": 500.0, "currency": "INR", "timestamp": base_time + timedelta(hours=2), "status": "captured",
            "is_fraud": False, "is_fraud_ground_truth": False, "fraud_archetype": "none", "fraud_case_id": None
        },
    ]

    return {
        "merchants": merchants,
        "customers": customers,
        "devices": devices,
        "payment_instruments": payment_instruments,
        "transactions": transactions,
    }


class TestPointInTimeCorrectness:
    """Verify exact feature calculations and point-in-time causality."""

    def test_first_transaction_has_zero_history(self, mock_dataset):
        pipeline = FeaturePipeline()
        df = pipeline.process_dataset(**mock_dataset)

        row1 = df[df["transaction_id"] == 1].iloc[0]
        assert row1["cust_txn_count_prev"] == 0
        assert row1["cust_is_first_txn"] == 1
        assert row1["velocity_txn_count_1h"] == 0
        assert row1["velocity_amount_sum_1h"] == 0.0
        assert row1["cust_days_since_last_txn"] == -1.0

    def test_second_transaction_has_exact_prior_stats(self, mock_dataset):
        pipeline = FeaturePipeline()
        df = pipeline.process_dataset(**mock_dataset)

        row2 = df[df["transaction_id"] == 2].iloc[0]
        assert row2["cust_txn_count_prev"] == 1
        assert row2["cust_is_first_txn"] == 0
        assert row2["cust_amount_mean_prev"] == 1000.0
        assert row2["cust_amount_sum_prev"] == 1000.0
        assert row2["velocity_txn_count_1h"] == 1
        assert row2["velocity_amount_sum_1h"] == 1000.0
        assert row2["cust_days_since_last_txn"] == pytest.approx(30.0 / 1440.0, rel=1e-3)

    def test_velocity_window_eviction(self, mock_dataset):
        pipeline = FeaturePipeline()
        df = pipeline.process_dataset(**mock_dataset)

        row3 = df[df["transaction_id"] == 3].iloc[0]
        # At 11:15 AM: Txn 1 (10:00 AM) is 75 min ago (> 1h), Txn 2 (10:30 AM) is 45 min ago (< 1h)
        assert row3["velocity_txn_count_1h"] == 1
        assert row3["velocity_amount_sum_1h"] == 2000.0
        # Both Txn 1 and Txn 2 are within 24h
        assert row3["velocity_txn_count_24h"] == 2
        assert row3["velocity_amount_sum_24h"] == 3000.0

    def test_new_device_detection(self, mock_dataset):
        pipeline = FeaturePipeline()
        df = pipeline.process_dataset(**mock_dataset)

        row1 = df[df["transaction_id"] == 1].iloc[0]
        row2 = df[df["transaction_id"] == 2].iloc[0]
        row3 = df[df["transaction_id"] == 3].iloc[0]

        # Txn 1: Device 1 used for the first time by Cust 1
        assert row1["device_is_new_for_cust"] == 1
        # Txn 2: Device 1 used again by Cust 1 -> NOT new
        assert row2["device_is_new_for_cust"] == 0
        # Txn 3: Device 2 introduced for Cust 1 -> IS new! (ATO indicator)
        assert row3["device_is_new_for_cust"] == 1


class TestBoundaryConditions:
    """Verify exact rolling window boundary conditions."""

    def test_exact_one_hour_boundary(self):
        vel = CustomerVelocityState(customer_id=100)
        t0 = datetime(2025, 1, 1, 12, 0, 0)
        config = FeatureConfig()

        # Add transaction at 12:00:00
        vel.update(t0, 500.0)

        # Check at 12:59:59 (inside 1h window: 3599s)
        f_inside = vel.compute_features(t0 + timedelta(seconds=3599), config)
        assert f_inside["velocity_txn_count_1h"] == 1

        # Check at 13:00:00 (exactly on 3600s boundary: cutoff is ts - 3600, t0 == cutoff -> included)
        f_exact = vel.compute_features(t0 + timedelta(seconds=3600), config)
        assert f_exact["velocity_txn_count_1h"] == 1

        # Check at 13:00:01 (3601s -> outside 1h window)
        f_outside = vel.compute_features(t0 + timedelta(seconds=3601), config)
        assert f_outside["velocity_txn_count_1h"] == 0


class TestNumericalStabilityAndColdStart:
    """Verify handling of new entities and mathematical edge cases."""

    def test_cold_start_all_entities(self):
        c_state = CustomerHistoryState(1, datetime(2025, 1, 1), typical_amount=1500.0)
        m_state = MerchantHistoryState(1, datetime(2025, 1, 1), typical_order_value=2500.0)
        d_state = DeviceHistoryState(1, datetime(2025, 1, 1))
        pi_state = PaymentInstrumentHistoryState(1, datetime(2025, 1, 1))
        config = FeatureConfig()

        now = datetime(2025, 1, 1, 10, 0, 0)
        c_feats = c_state.compute_features(500.0, now, config)
        m_feats = m_state.compute_features(500.0, now, config)
        d_feats = d_state.compute_features(1, now, config)
        pi_feats = pi_state.compute_features(now, config)

        assert c_feats["cust_txn_count_prev"] == 0
        assert c_feats["cust_amount_zscore"] == 0.0
        assert m_feats["merchant_txn_count_prev"] == 0
        assert d_feats["device_distinct_cust_prev"] == 0
        assert pi_feats["pi_distinct_cust_prev"] == 0

    def test_zero_variance_zscore(self):
        c_state = CustomerHistoryState(1, datetime(2025, 1, 1))
        config = FeatureConfig()
        t0 = datetime(2025, 1, 1, 10, 0, 0)

        # Two identical transactions -> std == 0
        c_state.update(1000.0, t0, "captured")
        c_state.update(1000.0, t0 + timedelta(hours=1), "captured")

        feats = c_state.compute_features(1000.0, t0 + timedelta(hours=2), config)
        assert feats["cust_amount_std_prev"] == 0.0
        assert feats["cust_amount_zscore"] == 0.0  # Does not divide by zero!


class TestLeakageVerificationSuite:
    """Verify the automated leakage checker and deliberate test."""

    def test_leakage_checker_passes_on_valid_data(self, mock_dataset):
        pipeline = FeaturePipeline()
        df = pipeline.process_dataset(**mock_dataset)
        checker = LeakageChecker(df)
        report = checker.run_all_checks()
        assert report["is_valid"] is True
        assert len(report["errors"]) == 0

    def test_deliberate_leakage_test_catches_invalid_feature(self, mock_dataset):
        pipeline = FeaturePipeline()
        df = pipeline.process_dataset(**mock_dataset)
        # Verify that deliberately injecting future fields is caught and raises AssertionError
        assert run_deliberate_leakage_test(df) is True

    def test_reproducibility(self, mock_dataset):
        pipeline1 = FeaturePipeline()
        df1 = pipeline1.process_dataset(**mock_dataset)

        pipeline2 = FeaturePipeline()
        df2 = pipeline2.process_dataset(**mock_dataset)

        pd.testing.assert_frame_equal(df1, df2)

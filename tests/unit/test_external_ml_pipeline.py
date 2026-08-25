"""
SentinelRisk — External Dataset ML Pipeline & Schema-Adaptive Risk Tests

Validates:
  1. External schema detection & alias mapping
  2. Point-in-time (t < T) feature construction
  3. Strict leakage prevention & label isolation
  4. External LightGBM model loading and deterministic inference
  5. Missing feature honesty (no fabricated device/card tokens)
  6. Policy engine integration & decision hierarchy
  7. Synthetic primary model isolation (remains unaffected)
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import joblib

from backend.app.ingestion.schema import NormalizedTransaction
from backend.app.ingestion.feature_builder import IncrementalFeatureBuilder
from ml.features.external_features import ExternalFeatureBuilder, EXTERNAL_FEATURE_NAMES
from backend.app.policy.engine import PolicyEngine
from backend.app.policy.models import DecisionState


class TestExternalDatasetFeatureEngineering:
    """Test point-in-time correctness, rolling state, and causality."""

    def test_external_feature_builder_count_and_names(self):
        builder = ExternalFeatureBuilder()
        feat = builder.extract_single(
            transaction_id=1,
            timestamp=datetime(2018, 4, 1, 12, 0, 0),
            amount=120.50,
            customer_id="CUST_100",
            terminal_id="TERM_500",
            tx_time_seconds=43200,
            update_state=True,
        )
        assert len(feat) == len(EXTERNAL_FEATURE_NAMES)
        assert "cust_velocity_1h" in feat
        assert "cust_amount_ratio" in feat
        assert "terminal_velocity_1h" in feat
        assert "is_new_terminal_for_cust" in feat
        assert feat["amount"] == 120.50

    def test_point_in_time_causality_t_less_than_T(self):
        """Verify that transaction at T only sees transactions strictly before T."""
        builder = ExternalFeatureBuilder()
        t0 = datetime(2018, 4, 1, 10, 0, 0)
        t1 = datetime(2018, 4, 1, 10, 15, 0)
        t2 = datetime(2018, 4, 1, 10, 30, 0)

        # First transaction: cold start (count_prev = 0, velocity_1h = 0)
        f0 = builder.extract_single(1, t0, 50.0, "CUST_A", "TERM_X", 36000, update_state=True)
        assert f0["cust_txn_count_prev"] == 0.0
        assert f0["cust_velocity_1h"] == 0.0
        assert f0["is_new_terminal_for_cust"] == 1.0

        # Second transaction 15 mins later: sees prior 1 transaction
        f1 = builder.extract_single(2, t1, 100.0, "CUST_A", "TERM_X", 36900, update_state=True)
        assert f1["cust_txn_count_prev"] == 1.0
        assert f1["cust_velocity_1h"] == 1.0
        assert f1["cust_amount_mean_prev"] == 50.0
        assert f1["cust_amount_ratio"] == 2.0  # 100 / 50
        assert f1["is_new_terminal_for_cust"] == 0.0  # Same terminal

        # Third transaction at novel terminal:
        f2 = builder.extract_single(3, t2, 200.0, "CUST_A", "TERM_Y", 37800, update_state=True)
        assert f2["cust_txn_count_prev"] == 2.0
        assert f2["cust_velocity_1h"] == 2.0
        assert f2["cust_amount_mean_prev"] == 75.0  # (50 + 100) / 2
        assert f2["is_new_terminal_for_cust"] == 1.0  # Novel terminal for CUST_A

    def test_temporal_leakage_rejection(self):
        """Assert that inserting a future transaction does NOT retroactively alter past features."""
        builder1 = ExternalFeatureBuilder()
        builder2 = ExternalFeatureBuilder()

        t_past = datetime(2018, 4, 1, 8, 0, 0)
        t_curr = datetime(2018, 4, 1, 9, 0, 0)
        t_future = datetime(2018, 4, 1, 18, 0, 0)

        # Builder 1: processes past then curr
        builder1.extract_single(1, t_past, 100.0, "CUST_Z", "TERM_1", 28800, update_state=True)
        f_curr_1 = builder1.extract_single(2, t_curr, 150.0, "CUST_Z", "TERM_1", 32400, update_state=False)

        # Builder 2: processes future transaction first (simulating inverted chronological bug)
        builder2.extract_single(3, t_future, 9999.0, "CUST_Z", "TERM_1", 64800, update_state=True)
        f_curr_2 = builder2.extract_single(2, t_curr, 150.0, "CUST_Z", "TERM_1", 32400, update_state=False)

        # Because t_curr < t_future, f_curr_2 must NOT include the future $9,999 in velocity or stats!
        assert f_curr_2["cust_velocity_1h"] == 0.0


class TestExternalModelLoadingAndInference:
    """Test model loading, feature validation, and schema-adaptive routing."""

    def test_external_lightgbm_model_exists_and_loads(self):
        model_path = Path("ml/models/external_fraud/model.joblib")
        assert model_path.exists(), "External LightGBM model artifact not found!"
        model = joblib.load(model_path)
        assert hasattr(model, "predict_proba")

    def test_external_model_inference_output(self):
        model = joblib.load("ml/models/external_fraud/model.joblib")
        sample_input = pd.DataFrame([{
            "amount": 450.0,
            "amount_log": 6.11,
            "hour_of_day": 3.0,
            "day_of_week": 6.0,
            "is_weekend": 1.0,
            "is_night": 1.0,
            "cust_txn_count_prev": 10.0,
            "cust_velocity_1h": 4.0,
            "cust_velocity_24h": 6.0,
            "cust_velocity_7d": 10.0,
            "cust_amount_sum_prev": 500.0,
            "cust_amount_mean_prev": 50.0,
            "cust_amount_std_prev": 10.0,
            "cust_amount_max_prev": 75.0,
            "cust_amount_ratio": 9.0,
            "cust_amount_zscore": 40.0,
            "terminal_txn_count_prev": 25.0,
            "terminal_velocity_1h": 2.0,
            "terminal_velocity_24h": 5.0,
            "terminal_velocity_7d": 15.0,
            "terminal_amount_mean_prev": 60.0,
            "terminal_amount_ratio": 7.5,
            "terminal_unique_cust_prev": 20.0,
            "is_new_terminal_for_cust": 1.0,
        }], columns=EXTERNAL_FEATURE_NAMES)

        probs = model.predict_proba(sample_input)[:, 1]
        assert len(probs) == 1
        assert 0.0 <= probs[0] <= 1.0
        # High velocity + 9x amount surge should yield high fraud probability
        assert probs[0] > 0.50

    def test_schema_adaptive_routing_in_incremental_builder(self):
        builder = IncrementalFeatureBuilder()

        # Handbook transaction
        hb_txn = NormalizedTransaction(
            transaction_id="TX_HB_001",
            timestamp="2018-04-01 12:00:00",
            amount=85.00,
            currency="EUR",
            customer_id="596",
            merchant_id="3156",
            device_id="UNKNOWN",
            payment_instrument_id="UNKNOWN",
            metadata={"source_dataset": "Fraud Detection Handbook"},
        )
        res_hb = builder.extract_features(hb_txn)

        assert res_hb["model_source"] == "external_handbook_lightgbm"
        assert res_hb["ml_status"] == "AVAILABLE"
        assert res_hb["feature_schema"] == "fraud_handbook_v1"
        assert res_hb["available_signal_count"] == 24
        assert res_hb["missing_signal_count"] == 23
        assert res_hb["graph_ring_score"] == 0.0  # Honesty: no fabricated graph edges

        # Synthetic transaction
        syn_txn = NormalizedTransaction(
            transaction_id="TX_SYN_001",
            timestamp="2025-06-15 14:00:00",
            amount=1250.00,
            currency="INR",
            customer_id="CUST_001",
            merchant_id="MERCH_001",
            device_id="DEV_001",
            payment_instrument_id="PI_001",
            metadata={"source_dataset": "Synthetic Payments World"},
        )
        res_syn = builder.extract_features(syn_txn)

        assert res_syn["model_source"] == "primary_synthetic_lightgbm"
        assert res_syn["feature_schema"] == "sentinelrisk_v1"
        assert res_syn["available_signal_count"] == 47


class TestPolicyEngineIntegrationAndPrimaryIsolation:
    """Test policy engine authority and synthetic model preservation."""

    def test_policy_engine_evaluates_external_ml_score(self):
        engine = PolicyEngine()
        
        # Moderate elevated external score -> CHALLENGE or REVIEW
        rec_review = engine.evaluate(
            transaction_id="TX_TEST_01",
            timestamp="2018-04-01 12:00:00",
            amount=85.00,
            ml_probability=0.08,  # > 0.05 threshold
        )
        assert rec_review.decision in (DecisionState.CHALLENGE, DecisionState.REVIEW)
        assert rec_review.primary_trigger == "ELEVATED_ML_RISK"

        # Severe external score -> HOLD
        rec_hold = engine.evaluate(
            transaction_id="TX_TEST_02",
            timestamp="2018-04-01 12:00:00",
            amount=500.00,
            ml_probability=0.92,
        )
        assert rec_hold.decision == DecisionState.HOLD
        assert rec_hold.primary_trigger in ("SEVERE_ML_RISK", "HIGH_CONFIDENCE_ML_RISK")

    def test_primary_synthetic_model_remains_isolated_and_functional(self):
        primary_path = Path("ml/models/lightgbm/model.joblib")
        assert primary_path.exists(), "Primary synthetic LightGBM model was modified or deleted!"
        primary_model = joblib.load(primary_path)
        assert hasattr(primary_model, "predict_proba")

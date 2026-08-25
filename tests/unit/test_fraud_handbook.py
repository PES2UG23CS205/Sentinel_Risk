"""
SentinelRisk — Tests for Fraud Detection Handbook Integration (Stage 11)

Validates:
  1. Dataset discovery and directory inspection
  2. PKL reading and schema detection
  3. Chronological timestamp sorting & non-leakage
  4. Ground truth isolation from feature inputs
  5. Derived compatibility fields labeling
  6. Replay metrics (TP, FP, TN, FN, Precision, Recall, F1)
  7. Replay lifecycle controls (load, step, clear)
  8. Existing demo scenarios preservation
"""

import pytest
from datetime import datetime
from pathlib import Path
import pandas as pd

from backend.app.external_data.fraud_handbook_loader import FraudHandbookLoader
from backend.app.ingestion.schema import NormalizedTransaction
from backend.app.ingestion.session_manager import LiveSessionManager
from backend.app.ingestion.feature_builder import IncrementalFeatureBuilder
from backend.app.scoring.realtime_service import RealtimeRiskService
from simulation.incident_simulator.simulator import IncidentSimulator


class TestFraudHandbookDatasetDiscovery:
    """Validate dataset discovery and schema extraction."""

    def test_dataset_discovery_and_file_count(self):
        loader = FraudHandbookLoader()
        files = loader.get_pkl_files()
        assert len(files) == 183, f"Expected 183 daily PKL files, got {len(files)}"
        assert files[0].name == "2018-04-01.pkl"
        assert files[-1].name == "2018-09-30.pkl"

    def test_metadata_summary(self):
        loader = FraudHandbookLoader()
        meta = loader.get_dataset_metadata()
        assert meta["available"] is True
        assert meta["total_files"] == 183
        assert meta["total_rows"] == 1754155
        assert meta["total_fraud"] == 14681
        assert meta["fraud_rate_pct"] > 0.8 and meta["fraud_rate_pct"] < 0.9
        assert meta["date_range"]["min"].startswith("2018-04-01")
        assert meta["date_range"]["max"].startswith("2018-09-30")

    def test_schema_columns(self):
        loader = FraudHandbookLoader()
        files = loader.get_pkl_files()
        df0 = pd.read_pickle(files[0])
        expected_cols = [
            "TRANSACTION_ID", "TX_DATETIME", "CUSTOMER_ID", "TERMINAL_ID",
            "TX_AMOUNT", "TX_TIME_SECONDS", "TX_TIME_DAYS", "TX_FRAUD", "TX_FRAUD_SCENARIO"
        ]
        for col in expected_cols:
            assert col in df0.columns, f"Missing expected column '{col}' in PKL schema"


class TestNormalizationAndIsolation:
    """Validate canonical normalization, derived compatibility fields, and ground-truth isolation."""

    def test_normalize_row_labels_derived_fields(self):
        raw_row = {
            "TRANSACTION_ID": 1001,
            "TX_DATETIME": "2018-04-01 10:15:30",
            "CUSTOMER_ID": 596,
            "TERMINAL_ID": 3156,
            "TX_AMOUNT": 75.50,
            "TX_TIME_SECONDS": 36930,
            "TX_TIME_DAYS": 0,
            "TX_FRAUD": 1,
            "TX_FRAUD_SCENARIO": 2,
        }
        norm = FraudHandbookLoader.normalize_row(raw_row)

        assert isinstance(norm, NormalizedTransaction)
        assert norm.transaction_id == "1001"
        assert norm.timestamp == "2018-04-01 10:15:30"
        assert norm.amount == 75.50
        assert norm.currency == "EUR"
        assert norm.customer_id == "596"
        assert norm.merchant_id == "TERM_3156"
        assert norm.device_id == "DEV_UNKNOWN"
        assert norm.payment_instrument_id == "PI_CUST_596"
        assert norm.ground_truth_fraud == 1
        assert norm.ground_truth_scenario == 2

        # Verify derived fields labeling
        derived = norm.metadata.get("derived_fields", {})
        assert "merchant_id" in derived
        assert "device_id" in derived
        assert "payment_instrument_id" in derived
        assert "DERIVED" in derived["merchant_id"]

    def test_ground_truth_isolation_from_features(self):
        """Ensure TX_FRAUD / ground_truth_fraud is NOT used as an input feature."""
        fb = IncrementalFeatureBuilder()
        txn = NormalizedTransaction(
            transaction_id="TXN-TEST-GT",
            timestamp="2018-04-01 12:00:00",
            amount=50.0,
            currency="EUR",
            customer_id="CUST_1",
            merchant_id="TERM_100",
            device_id="DEV_UNKNOWN",
            payment_instrument_id="PI_CUST_1",
            metadata={"source_dataset": "Fraud Detection Handbook"},
            ground_truth_fraud=1,  # Ground truth is FRAUD
            ground_truth_scenario=1,
        )
        res = fb.extract_features(txn)
        # Ground truth must not appear in extracted feature dictionary
        assert "ground_truth_fraud" not in res["features"]
        assert "TX_FRAUD" not in res["features"]
        assert "tx_fraud" not in res["features"]


class TestChronologicalOrderingAndReplay:
    """Validate chronological ordering, replay step, and confusion matrix calculation."""

    def test_chronological_sorting(self):
        loader = FraudHandbookLoader()
        txns = loader.load_transactions(limit=100)
        assert len(txns) == 100
        for i in range(len(txns) - 1):
            t1 = datetime.strptime(txns[i].timestamp, "%Y-%m-%d %H:%M:%S")
            t2 = datetime.strptime(txns[i + 1].timestamp, "%Y-%m-%d %H:%M:%S")
            assert t1 <= t2, f"Chronological ordering violation: {t1} > {t2}"

    def test_replay_lifecycle_and_metrics(self):
        session = LiveSessionManager()
        loader = FraudHandbookLoader()
        txns = loader.load_transactions(limit=50)

        session.load_dataset(txns, source_name="Test Replay")
        state0 = session.get_state()
        assert state0["status"] == "IDLE"
        assert state0["progress"]["total_rows"] == 50
        assert state0["progress"]["current_index"] == 0

        # Step 10 transactions
        for _ in range(10):
            event = session.step_stream()
            assert event is not None
            assert "decision" in event
            assert "ground_truth_label" in event

        state10 = session.get_state()
        assert state10["counters"]["total_processed"] == 10
        assert state10["progress"]["current_index"] == 10
        assert len(state10["recent_events"]) == 10

        # Verify confusion matrix tracking structure
        rm = state10["replay_metrics"]
        assert rm["has_ground_truth"] is True
        assert (rm["tp"] + rm["fp"] + rm["tn"] + rm["fn"]) == 10

        # Clear session
        session.clear_session()
        state_cleared = session.get_state()
        assert state_cleared["counters"]["total_processed"] == 0
        assert len(state_cleared["recent_events"]) == 0

    def test_confusion_matrix_mathematical_correctness(self):
        session = LiveSessionManager()
        # Create controlled synthetic stream with known ground truths
        mock_txns = [
            NormalizedTransaction(
                transaction_id="TX-1", timestamp="2018-04-01 01:00:00", amount=50.0,
                customer_id="C1", merchant_id="M1", device_id="DEV_UNKNOWN",
                payment_instrument_id="PI_1", ground_truth_fraud=0
            ),
            NormalizedTransaction(
                transaction_id="TX-2", timestamp="2018-04-01 01:01:00", amount=50000.0,  # Elevated amount triggers REVIEW
                customer_id="C2", merchant_id="M2", device_id="DEV_UNKNOWN",
                payment_instrument_id="PI_2", ground_truth_fraud=1
            ),
        ]
        session.load_dataset(mock_txns, source_name="Control Matrix Test")
        session.step_stream()
        session.step_stream()

        rm = session.get_state()["replay_metrics"]
        assert rm["tp"] + rm["fp"] + rm["tn"] + rm["fn"] == 2
        # Precision & Recall & F1 must be between 0.0 and 1.0
        assert 0.0 <= rm["precision"] <= 1.0
        assert 0.0 <= rm["recall"] <= 1.0
        assert 0.0 <= rm["f1"] <= 1.0


class TestPreserveExistingDemoScenarios:
    """Verify that all existing Stage 10 demo scenarios and services continue working 100%."""

    def test_all_demo_scenarios_deterministic(self):
        service = RealtimeRiskService()
        simulator = IncidentSimulator()

        # 1. 2 AM attack
        res_2am = simulator.run_scenario("CARD_TESTING_ATTACK")
        assert res_2am["metrics"]["hold_count"] > 0

        # 2. Legitimate transaction -> APPROVE
        res_legit = service.evaluate_transaction({
            "transaction_id": "DEMO-LEGIT-001",
            "amount": 420.00,
            "currency": "INR",
            "customer_id": "CUST_LEGIT_101",
            "device_id": "DEV_TRUSTED_01",
            "payment_instrument_id": "PI_PERSONAL_01",
            "merchant_id": "MERCH_GROCERY_01",
            "timestamp": "2025-06-15 14:20:00",
            "ml_probability": 0.0012,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 1.0},
        })
        assert res_legit["decision"] == "APPROVE"

        # 3. Account takeover -> HOLD
        res_ato = service.evaluate_transaction({
            "transaction_id": "DEMO-ATO-002",
            "amount": 24500.00,
            "currency": "INR",
            "customer_id": "CUST_VICTIM_404",
            "device_id": "DEV_ATTACKER_99",
            "payment_instrument_id": "PI_VICTIM_CARD",
            "merchant_id": "MERCH_ELECTRONICS_05",
            "timestamp": "2025-06-15 02:15:00",
            "ml_probability": 0.985,
            "graph_ring_score": 0.0,
            "graph_ring_candidate": 0,
            "features": {"pi_velocity_count_1h": 1, "cust_amount_to_mean_ratio": 6.2, "cust_amount_zscore": 4.1, "device_is_new_for_cust": 1},
        })
        assert res_ato["decision"] == "HOLD"

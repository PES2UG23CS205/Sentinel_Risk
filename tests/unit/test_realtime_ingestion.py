"""
SentinelRisk — Real-Time Ingestion, Feature Builder & Live Streaming Tests

Tests:
  - Column mapping inference from aliases
  - CSV/JSON dataset parsing & validation
  - Incremental point-in-time feature extraction & cold-start logic
  - Live session coordinator, counters, and incident detection
  - Streaming REST API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.ingestion.schema import NormalizedTransaction, SchemaMapping, infer_schema_mapping
from backend.app.ingestion.validator import DatasetValidator
from backend.app.ingestion.feature_builder import IncrementalFeatureBuilder
from backend.app.ingestion.session_manager import LiveSessionManager


@pytest.fixture
def client():
    return TestClient(app)


class TestSchemaMappingAndValidation:
    """Test schema inference, parsing, and data validation."""

    def test_infer_schema_mapping_standard_aliases(self):
        cols = ["txn_id", "time", "amt", "user_id", "merch_id", "hardware_id", "card_token"]
        mapping = infer_schema_mapping(cols)
        assert mapping.transaction_id == "txn_id"
        assert mapping.timestamp == "time"
        assert mapping.amount == "amt"
        assert mapping.customer_id == "user_id"
        assert mapping.merchant_id == "merch_id"
        assert mapping.device_id == "hardware_id"
        assert mapping.payment_instrument_id == "card_token"

    def test_dataset_validation_valid_and_invalid_rows(self):
        raw_csv = """transaction_id,timestamp,amount,customer_id,merchant_id,device_id,payment_instrument_id
TXN-1,2025-06-01 10:00:00,500.00,CUST_1,MERCH_1,DEV_1,PI_1
TXN-2,2025-06-01 10:05:00,-50.00,CUST_2,MERCH_1,DEV_2,PI_2
TXN-3,invalid-date,200.00,CUST_3,MERCH_1,DEV_3,PI_3
TXN-1,2025-06-01 10:15:00,300.00,CUST_1,MERCH_1,DEV_1,PI_1
"""
        headers, rows = DatasetValidator.parse_raw_records(raw_csv, "csv")
        report = DatasetValidator.validate_and_normalize(rows, headers=headers)

        assert report.total_rows == 4
        assert report.valid_rows_count == 1  # Only TXN-1 (first) is completely valid
        assert report.invalid_rows_count == 3
        reasons = [r.reason for r in report.invalid_rows]
        assert any("Non-positive amount" in r for r in reasons)
        assert any("Unparsable timestamp" in r for r in reasons)
        assert any("Duplicate transaction ID" in r for r in reasons)


class TestIncrementalFeatureBuilder:
    """Test point-in-time safe stateful feature builder."""

    def test_cold_start_and_subsequent_history(self):
        builder = IncrementalFeatureBuilder()

        # 1. First transaction for CUST_A (Cold-Start)
        t1 = NormalizedTransaction(
            transaction_id="TX-1",
            timestamp="2025-06-01 10:00:00",
            amount=1000.0,
            customer_id="CUST_A",
            merchant_id="MERCH_1",
            device_id="DEV_A",
            payment_instrument_id="PI_A",
        )
        res1 = builder.extract_features(t1)
        assert res1["is_cold_start"] is True
        assert res1["features"]["cust_amount_to_mean_ratio"] == 1.0
        assert res1["features"]["device_is_new_for_cust"] == 0
        assert res1["features"]["pi_velocity_count_1h"] == 0

        # 2. Second transaction for CUST_A within 10 minutes on same card
        t2 = NormalizedTransaction(
            transaction_id="TX-2",
            timestamp="2025-06-01 10:10:00",
            amount=5000.0,
            customer_id="CUST_A",
            merchant_id="MERCH_1",
            device_id="DEV_B",  # New device!
            payment_instrument_id="PI_A",
        )
        res2 = builder.extract_features(t2)
        assert res2["is_cold_start"] is False
        assert res2["features"]["pi_velocity_count_1h"] == 1
        assert res2["features"]["cust_amount_to_mean_ratio"] == 5.0
        assert res2["features"]["device_is_new_for_cust"] == 1

    def test_graph_syndicate_ring_detection(self):
        builder = IncrementalFeatureBuilder()

        # 4 customers sharing same hardware device and card token
        for i in range(4):
            txn = NormalizedTransaction(
                transaction_id=f"TX-RING-{i}",
                timestamp=f"2025-06-01 12:{i*5:02d}:00",
                amount=3000.0,
                customer_id=f"CUST_MULE_{i}",
                merchant_id="MERCH_DIGITAL",
                device_id="DEV_SHARED_BOX",
                payment_instrument_id="PI_SHARED_CARD",
            )
            res = builder.extract_features(txn)
            if i >= 2:
                # Connected to 2+ customers on device and 2+ on card
                assert res["graph_ring_score"] >= 0.40
                assert res["graph_ring_candidate"] == 1


class TestLiveSessionManager:
    """Test session lifecycle, counters, and stream stepping."""

    def test_session_flow_and_counters(self):
        manager = LiveSessionManager()
        rows = [
            NormalizedTransaction(
                transaction_id=f"TX-{i}",
                timestamp=f"2025-06-01 10:{i:02d}:00",
                amount=100.0 + (i * 50),
                customer_id=f"CUST_{i}",
                merchant_id="MERCH_1",
                device_id=f"DEV_{i}",
                payment_instrument_id=f"PI_{i}",
            )
            for i in range(5)
        ]
        manager.load_dataset(rows, source_name="Unit Test Data")
        assert manager.counters["total_processed"] == 0

        # Step first 2 events
        e1 = manager.step_stream()
        assert e1 is not None
        assert manager.counters["total_processed"] == 1

        e2 = manager.step_stream()
        assert e2 is not None
        assert manager.counters["total_processed"] == 2

        state = manager.get_state()
        assert state["progress"]["current_index"] == 2
        assert state["progress"]["total_rows"] == 5

        # Clear session
        manager.clear_session()
        assert manager.counters["total_processed"] == 0
        assert len(manager.dataset_buffer) == 0


class TestStreamingAPIRoutes:
    """Test REST endpoints for streaming and data ingestion."""

    def test_upload_preview_and_validate(self, client):
        sample_csv = "txn_id,created,val,user\nTX-1,2025-06-01 10:00:00,500.00,USER-1\n"
        res = client.post("/stream/upload/preview", json={"content": sample_csv, "file_type": "csv"})
        assert res.status_code == 200
        data = res.json()
        assert data["total_rows"] == 1
        assert "txn_id" in data["columns"]

    def test_session_start_and_single_eval(self, client):
        sample_csv = "transaction_id,timestamp,amount,customer_id,merchant_id,device_id,payment_instrument_id\nTX-LIVE-1,2025-06-01 10:00:00,450.00,CUST_1,MERCH_1,DEV_1,PI_1\n"
        res = client.post("/stream/session/start", json={"content": sample_csv, "file_type": "csv"})
        assert res.status_code == 200
        assert res.json()["valid_rows_loaded"] == 1

        # Single evaluation
        single_res = client.post(
            "/stream/evaluate-single",
            json={
                "transaction_id": "TX-ADHOC-99",
                "timestamp": "2025-06-01 11:00:00",
                "amount": 25000.0,
                "currency": "INR",
                "customer_id": "CUST_99",
                "merchant_id": "MERCH_1",
                "device_id": "DEV_NEW",
                "payment_instrument_id": "PI_1",
            },
        )
        assert single_res.status_code == 200
        d = single_res.json()
        assert d["event"]["transaction_id"] == "TX-ADHOC-99"
        assert d["event"]["decision"] in ("APPROVE", "REVIEW", "HOLD")

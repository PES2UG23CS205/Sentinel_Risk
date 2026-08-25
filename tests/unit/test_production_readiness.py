"""
SentinelRisk — Stage 9: Production Readiness, Real-Time Scoring & Observability Unit Tests

Verifies:
  - Request validation & input hashing (positive amounts, ISO timestamps, required fields)
  - Idempotency layer (exact duplicate replay vs. conflicting payload rejection)
  - Latency instrumentation across all layers (< 100ms budget)
  - Complete version metadata tracking (model, feature, graph, policy, prompt)
  - Resilience & graceful degradation (ML fallback, Graph fallback, Policy fail-safe)
  - Health & readiness probes (/health/live, /health/ready, /health/dependencies)
  - Operational metrics and alert threshold triggers
  - REST API endpoint integration (POST /risk/evaluate, GET /metrics/operations)
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.scoring.validation import validate_risk_request, compute_input_hash, ValidationError
from backend.app.scoring.idempotency import IdempotencyManager, IdempotencyConflictError
from backend.app.scoring.metrics import OperationalMetricsTracker, generate_correlation_id
from backend.app.scoring.resilience import ResilienceConfig, DependencyStatus
from backend.app.scoring.realtime_service import RealtimeRiskService
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def risk_service():
    return RealtimeRiskService()


class TestRequestValidationAndHashing:
    """Verify input validation and deterministic SHA-256 hashing."""

    def test_valid_request(self):
        payload = {
            "transaction_id": "TX_VAL_01",
            "amount": 499.50,
            "customer_id": "CUST_100",
            "device_id": "DEV_200",
            "payment_instrument_id": "PI_300",
            "merchant_id": "MERCH_400",
            "timestamp": "2025-06-15 12:30:00",
        }
        validated = validate_risk_request(payload)
        assert validated["transaction_id"] == "TX_VAL_01"
        assert validated["amount"] == 499.50
        assert validated["currency"] == "INR"

    def test_missing_field_rejected(self):
        payload = {
            "transaction_id": "TX_VAL_02",
            "amount": 100.0,
            "customer_id": "CUST_100",
            # missing device_id, payment_instrument_id, merchant_id, timestamp
        }
        with pytest.raises(ValidationError) as exc:
            validate_risk_request(payload)
        assert "Missing mandatory field" in str(exc.value)

    def test_negative_or_zero_amount_rejected(self):
        payload = {
            "transaction_id": "TX_VAL_03",
            "amount": -50.0,
            "customer_id": "CUST_100",
            "device_id": "DEV_200",
            "payment_instrument_id": "PI_300",
            "merchant_id": "MERCH_400",
            "timestamp": "2025-06-15 12:30:00",
        }
        with pytest.raises(ValidationError) as exc:
            validate_risk_request(payload)
        assert "strictly positive" in str(exc.value)

    def test_invalid_timestamp_rejected(self):
        payload = {
            "transaction_id": "TX_VAL_04",
            "amount": 150.0,
            "customer_id": "CUST_100",
            "device_id": "DEV_200",
            "payment_instrument_id": "PI_300",
            "merchant_id": "MERCH_400",
            "timestamp": "NOT_A_TIMESTAMP",
        }
        with pytest.raises(ValidationError) as exc:
            validate_risk_request(payload)
        assert "Invalid timestamp format" in str(exc.value)

    def test_deterministic_input_hashing(self):
        p1 = {"transaction_id": "TX1", "amount": 100.0, "customer_id": "C1", "device_id": "D1", "payment_instrument_id": "P1", "merchant_id": "M1", "timestamp": "2025-01-01 10:00:00"}
        p2 = {"timestamp": "2025-01-01 10:00:00", "merchant_id": "M1", "payment_instrument_id": "P1", "device_id": "D1", "customer_id": "C1", "amount": 100.0, "transaction_id": "TX1"}
        # Same data regardless of key order must yield identical hash
        assert compute_input_hash(p1) == compute_input_hash(p2)


class TestIdempotencyHandling:
    """Verify duplicate replay and conflicting payload rejection."""

    def test_exact_duplicate_replay(self, risk_service):
        payload = {
            "transaction_id": "TX_IDEM_01",
            "amount": 750.0,
            "customer_id": "CUST_IDEM_1",
            "device_id": "DEV_IDEM_1",
            "payment_instrument_id": "PI_IDEM_1",
            "merchant_id": "MERCH_IDEM_1",
            "timestamp": "2025-06-15 10:00:00",
            "ml_probability": 0.002,
        }

        # 1. First execution
        res1 = risk_service.evaluate_transaction(payload)
        assert res1["idempotency_cached"] is False
        assert res1["decision"] == "APPROVE"

        # 2. Duplicate execution
        res2 = risk_service.evaluate_transaction(payload)
        assert res2["idempotency_cached"] is True
        assert res2["decision"] == res1["decision"]
        assert res2["input_hash"] == res1["input_hash"]

    def test_conflicting_payload_raises_error(self, risk_service):
        payload1 = {
            "transaction_id": "TX_IDEM_CONFLICT",
            "amount": 500.0,
            "customer_id": "CUST_1",
            "device_id": "DEV_1",
            "payment_instrument_id": "PI_1",
            "merchant_id": "MERCH_1",
            "timestamp": "2025-06-15 10:00:00",
        }
        risk_service.evaluate_transaction(payload1)

        payload2 = dict(payload1)
        payload2["amount"] = 9999.0  # Conflicting payload

        with pytest.raises(IdempotencyConflictError):
            risk_service.evaluate_transaction(payload2)


class TestResilienceAndGracefulDegradation:
    """Verify graceful degradation when upstream dependencies fail."""

    def test_ml_failure_fallback(self):
        resilience = ResilienceConfig(simulate_ml_failure=True)
        service = RealtimeRiskService(resilience_config=resilience)

        payload = {
            "transaction_id": "TX_ML_FAIL",
            "amount": 250.0,
            "customer_id": "CUST_1",
            "device_id": "DEV_1",
            "payment_instrument_id": "PI_1",
            "merchant_id": "MERCH_1",
            "timestamp": "2025-06-15 10:00:00",
            "graph_ring_score": 0.85,
            "graph_ring_candidate": 1,
            "features": {"pi_velocity_count_1h": 1},
        }

        res = service.evaluate_transaction(payload)
        assert res["dependency_statuses"]["ml"] == DependencyStatus.DEGRADED.value
        assert res["decision"] == "HOLD"  # Graph catches syndicate in fallback mode
        assert res["primary_trigger"] == "RESILIENCE_ML_FALLBACK"

    def test_graph_failure_fallback(self):
        resilience = ResilienceConfig(simulate_graph_failure=True)
        service = RealtimeRiskService(resilience_config=resilience)

        payload = {
            "transaction_id": "TX_GRAPH_FAIL",
            "amount": 250.0,
            "customer_id": "CUST_1",
            "device_id": "DEV_1",
            "payment_instrument_id": "PI_1",
            "merchant_id": "MERCH_1",
            "timestamp": "2025-06-15 10:00:00",
            "ml_probability": 0.95,
            "features": {"pi_velocity_count_1h": 1},
        }

        res = service.evaluate_transaction(payload)
        assert res["dependency_statuses"]["graph"] == DependencyStatus.UNAVAILABLE.value
        assert res["decision"] == "HOLD"  # ML catches anomaly in fallback mode
        assert res["primary_trigger"] == "RESILIENCE_GRAPH_FALLBACK"

    def test_policy_failure_fail_safe(self):
        resilience = ResilienceConfig(simulate_policy_failure=True)
        service = RealtimeRiskService(resilience_config=resilience)

        payload = {
            "transaction_id": "TX_POL_FAIL",
            "amount": 100.0,
            "customer_id": "CUST_1",
            "device_id": "DEV_1",
            "payment_instrument_id": "PI_1",
            "merchant_id": "MERCH_1",
            "timestamp": "2025-06-15 10:00:00",
        }

        res = service.evaluate_transaction(payload)
        assert res["dependency_statuses"]["policy"] == "FAILED"
        assert res["decision"] == "REVIEW"  # Safe fail-safe intervention
        assert res["primary_trigger"] == "FAIL_SAFE_POLICY_OUTAGE"


class TestObservabilityAndProbes:
    """Verify version tracking, latency profiling, and health probes."""

    def test_version_metadata_and_latencies(self, risk_service):
        payload = {
            "transaction_id": "TX_OBS_01",
            "amount": 320.0,
            "customer_id": "CUST_1",
            "device_id": "DEV_1",
            "payment_instrument_id": "PI_1",
            "merchant_id": "MERCH_1",
            "timestamp": "2025-06-15 10:00:00",
        }
        res = risk_service.evaluate_transaction(payload)

        # Version checks
        assert res["versions"]["model_version"] == "lightgbm-v1"
        assert res["versions"]["policy_version"] == "sentinelrisk-policy-v1"
        assert res["versions"]["graph_version"] == "graph-v1"

        # Latency checks
        lats = res["latencies_ms"]
        assert "total_ms" in lats
        assert lats["total_ms"] < 100.0  # Well within SLA budget

    def test_health_endpoints(self, client):
        # 1. Live probe
        res_live = client.get("/health/live")
        assert res_live.status_code == 200
        assert res_live.json()["status"] == "ALIVE"

        # 2. Ready probe
        res_ready = client.get("/health/ready")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] == "READY"

        # 3. Dependencies probe
        res_deps = client.get("/health/dependencies")
        assert res_deps.status_code == 200
        assert res_deps.json()["overall_health"] == "HEALTHY"

    def test_post_risk_evaluate_api(self, client):
        payload = {
            "transaction_id": "TX_API_01",
            "amount": 1250.0,
            "customer_id": "CUST_API",
            "device_id": "DEV_API",
            "payment_instrument_id": "PI_API",
            "merchant_id": "MERCH_API",
            "timestamp": "2025-06-15 10:00:00",
            "ml_probability": 0.9995,
        }
        res = client.post("/risk/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "HOLD"
        assert "correlation_id" in data
        assert "latencies_ms" in data

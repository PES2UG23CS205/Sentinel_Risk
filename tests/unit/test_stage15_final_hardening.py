"""
Tests for Stage 15: Final Production Hardening, Benchmark Integrity & Operations Contracts
"""

import pytest
from pathlib import Path
import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.scoring.realtime_service import RealtimeRiskService

client = TestClient(app)


def test_overview_endpoint_contract():
    res = client.get("/dashboard/overview")
    assert res.status_code == 200
    data = res.json()
    assert "executive_kpis" in data
    assert "system_health" in data
    assert "version_metadata" in data
    assert data["version_metadata"]["policy_version"] == "sentinelrisk-policy-v1"


def test_model_health_endpoint_contract():
    res = client.get("/dashboard/model-health")
    assert res.status_code == 200
    data = res.json()
    assert "model_metadata" in data
    assert "overall_drift_status" in data
    assert "monitored_features" in data


def test_merchants_api_contract():
    res = client.get("/merchants/")
    assert res.status_code == 200
    data = res.json()
    assert "total_merchants" in data
    assert "merchants" in data


def test_idempotency_and_deterministic_replay():
    service = RealtimeRiskService()
    txn = {
        "transaction_id": "TXN_HARDEN_TEST_01",
        "amount": 1200.0,
        "currency": "INR",
        "customer_id": "C_TEST",
        "device_id": "D_TEST",
        "payment_instrument_id": "PI_TEST",
        "merchant_id": "M_TEST",
        "timestamp": "2025-06-15 12:00:00",
        "ml_probability": 0.005,
    }
    res1 = service.evaluate_transaction(txn)
    res2 = service.evaluate_transaction(txn)

    assert res1["decision"] == res2["decision"]
    assert res1["input_hash"] == res2["input_hash"]
    assert res2["idempotency_cached"] is True


def test_benchmark_artifacts_integrity():
    eval_dir = Path("evaluation/final")
    assert (eval_dir / "authoritative_final_benchmark.csv").exists()
    assert (eval_dir / "archetype_performance.csv").exists()
    assert (eval_dir / "friction_comparison.csv").exists()
    assert (eval_dir / "merchant_risk_summary.csv").exists()
    assert (eval_dir / "model_health_summary.csv").exists()

    df_bm = pd.read_csv(eval_dir / "authoritative_final_benchmark.csv")
    assert len(df_bm) >= 5
    assert "fraud_recall_pct" in df_bm.columns

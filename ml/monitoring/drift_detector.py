"""
SentinelRisk — Model & Feature Drift Monitoring Subsystem (Stage 13)

Calculates Population Stability Index (PSI) and monitors statistical feature distributions,
operational decision distributions, and model performance metrics.
"""

import math
import yaml
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd


def calculate_psi(expected: np.ndarray, actual: np.ndarray, bins: list[float] | int = 10, eps: float = 1e-4) -> float:
    """
    Compute Population Stability Index (PSI) between expected (baseline) and actual (inference) distributions.
    
    Formula:
        PSI = sum((Actual_pct - Expected_pct) * ln(Actual_pct / Expected_pct))
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)

    # Bin the data
    if isinstance(bins, list):
        bin_edges = np.array(bins)
    else:
        # Create quantiles or uniform bins based on expected
        bin_edges = np.linspace(min(np.min(expected), np.min(actual)), max(np.max(expected), np.max(actual)), bins + 1)

    expected_counts, _ = np.histogram(expected, bins=bin_edges)
    actual_counts, _ = np.histogram(actual, bins=bin_edges)

    # Add epsilon to prevent division by zero
    expected_pct = (expected_counts + eps) / (np.sum(expected_counts) + eps * len(expected_counts))
    actual_pct = (actual_counts + eps) / (np.sum(actual_counts) + eps * len(actual_counts))

    psi_val = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(max(0.0, psi_val))


class ModelDriftMonitor:
    """Statistical monitor tracking feature drift, distribution shifts, and operational metrics."""

    def __init__(self, config_path: str = "config/monitoring.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.baseline_data = self._load_baseline_features()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {
            "psi_thresholds": {"normal_threshold": 0.10, "watch_threshold": 0.25, "drift_threshold": 0.25},
            "training_baselines": {
                "model_name": "primary_synthetic_lightgbm",
                "model_version": "lightgbm-sentinel-v1",
                "training_date": "2025-06-11",
                "fraud_rate_pct": 1.28,
                "approval_rate_pct": 96.74,
                "challenge_rate_pct": 1.16,
                "review_rate_pct": 0.83,
                "hold_rate_pct": 1.28,
            },
        }

    def _load_baseline_features(self) -> dict[str, np.ndarray]:
        """Load frozen synthetic training baseline distributions for PSI calculation."""
        feat_path = Path("data/processed/features_train.csv")
        if feat_path.exists():
            try:
                df = pd.read_csv(feat_path, nrows=5000)
                baselines = {}
                if "amount" in df.columns:
                    baselines["amount"] = df["amount"].values
                if "cust_velocity_1h" in df.columns:
                    baselines["cust_velocity_1h"] = df["cust_velocity_1h"].values
                if "cust_amount_ratio" in df.columns:
                    baselines["cust_amount_ratio"] = df["cust_amount_ratio"].values
                if "hour" in df.columns:
                    baselines["transaction_hour"] = df["hour"].values
                return baselines
            except Exception:
                pass
        
        # Deterministic fallback synthetic distribution
        rng = np.random.default_rng(42)
        return {
            "amount": rng.lognormal(mean=6.5, sigma=1.2, size=1000),
            "cust_velocity_1h": rng.poisson(lam=1.2, size=1000),
            "cust_amount_ratio": rng.gamma(shape=2.0, scale=0.5, size=1000),
            "transaction_hour": rng.integers(low=0, high=24, size=1000),
            "risk_score": rng.beta(a=0.5, b=20.0, size=1000),
        }

    def evaluate_drift(self, current_events: list[dict]) -> dict:
        """
        Evaluate statistical drift between baseline training distributions and current events.
        """
        if not current_events:
            return self._empty_report()

        df_current = pd.DataFrame(current_events)
        features_report = []
        overall_drift_status = "NORMAL"

        # 1. Amount PSI
        if "amount" in df_current.columns:
            cur_amt = pd.to_numeric(df_current["amount"], errors="coerce").dropna().values
            base_amt = self.baseline_data.get("amount", np.array([500.0, 1000.0, 2000.0]))
            psi_amt = calculate_psi(base_amt, cur_amt, bins=[0, 500, 1500, 5000, 15000, 50000, 1000000])
            status_amt = "NORMAL" if psi_amt < 0.10 else ("WATCH" if psi_amt < 0.25 else "DRIFT")
            features_report.append({
                "feature": "amount",
                "description": "Transaction Amount (INR/EUR)",
                "psi": round(psi_amt, 4),
                "status": status_amt,
                "mean_value": round(float(np.mean(cur_amt)), 2) if len(cur_amt) > 0 else 0.0,
            })

        # 2. Customer Velocity PSI
        cur_vel = []
        for e in current_events:
            f = e.get("features", {})
            vel = f.get("cust_velocity_1h", f.get("cust_velocity_count_1h", 1.0))
            cur_vel.append(float(vel))
        if cur_vel:
            base_vel = self.baseline_data.get("cust_velocity_1h", np.array([1, 1, 2, 3]))
            psi_vel = calculate_psi(base_vel, np.array(cur_vel), bins=[0, 1, 2, 3, 5, 10, 100])
            status_vel = "NORMAL" if psi_vel < 0.10 else ("WATCH" if psi_vel < 0.25 else "DRIFT")
            features_report.append({
                "feature": "cust_velocity_1h",
                "description": "Customer 1h Velocity",
                "psi": round(psi_vel, 4),
                "status": status_vel,
                "mean_value": round(float(np.mean(cur_vel)), 2),
            })

        # 3. Spend Ratio PSI
        cur_ratio = []
        for e in current_events:
            f = e.get("features", {})
            ratio = f.get("cust_amount_to_mean_ratio", f.get("cust_amount_ratio", 1.0))
            cur_ratio.append(float(ratio))
        if cur_ratio:
            base_ratio = self.baseline_data.get("cust_amount_ratio", np.array([1.0, 1.2, 1.5]))
            psi_ratio = calculate_psi(base_ratio, np.array(cur_ratio), bins=[0.0, 0.8, 1.2, 2.0, 4.0, 6.0, 50.0])
            status_ratio = "NORMAL" if psi_ratio < 0.10 else ("WATCH" if psi_ratio < 0.25 else "DRIFT")
            features_report.append({
                "feature": "cust_amount_ratio",
                "description": "Customer Spend Ratio to Mean",
                "psi": round(psi_ratio, 4),
                "status": status_ratio,
                "mean_value": round(float(np.mean(cur_ratio)), 2),
            })

        # 4. Risk Score PSI
        cur_scores = [float(e.get("ml_probability", e.get("risk_score", 0.01))) for e in current_events]
        base_scores = self.baseline_data.get("risk_score", np.array([0.01, 0.02, 0.05, 0.10]))
        psi_score = calculate_psi(base_scores, np.array(cur_scores), bins=[0.0, 0.05, 0.25, 0.50, 0.80, 1.0])
        status_score = "NORMAL" if psi_score < 0.10 else ("WATCH" if psi_score < 0.25 else "DRIFT")
        features_report.append({
            "feature": "risk_score",
            "description": "Model Calibrated Fraud Probability",
            "psi": round(psi_score, 4),
            "status": status_score,
            "mean_value": round(float(np.mean(cur_scores)), 4),
        })

        # Determine overall drift
        if any(f["status"] == "DRIFT" for f in features_report):
            overall_drift_status = "DRIFT"
        elif any(f["status"] == "WATCH" for f in features_report):
            overall_drift_status = "WATCH"

        # Compute Operational Rate Comparison
        n_total = len(current_events)
        n_appr = sum(1 for e in current_events if e.get("decision") == "APPROVE")
        n_chal = sum(1 for e in current_events if e.get("decision") == "CHALLENGE")
        n_rev = sum(1 for e in current_events if e.get("decision") == "REVIEW")
        n_hold = sum(1 for e in current_events if e.get("decision") == "HOLD")

        gt_fraud = sum(1 for e in current_events if e.get("ground_truth_label") == "FRAUD")
        has_gt = any(e.get("ground_truth_label") in ("FRAUD", "LEGITIMATE") for e in current_events)

        base_cfg = self.config.get("training_baselines", {})

        return {
            "model_metadata": {
                "active_model": base_cfg.get("model_name", "primary_synthetic_lightgbm"),
                "model_version": base_cfg.get("model_version", "lightgbm-sentinel-v1"),
                "training_date": base_cfg.get("training_date", "2025-06-11"),
                "feature_schema": "sentinelrisk_v1_point_in_time",
                "monitoring_version": self.config.get("monitoring_version", "sentinelrisk-monitoring-v1"),
            },
            "overall_drift_status": overall_drift_status,
            "monitored_features": features_report,
            "operational_distributions": {
                "current_sample_size": n_total,
                "current_approval_rate_pct": round(n_appr / n_total * 100.0, 2) if n_total > 0 else 0.0,
                "baseline_approval_rate_pct": base_cfg.get("approval_rate_pct", 96.74),
                "current_challenge_rate_pct": round(n_chal / n_total * 100.0, 2) if n_total > 0 else 0.0,
                "baseline_challenge_rate_pct": base_cfg.get("challenge_rate_pct", 1.16),
                "current_review_rate_pct": round(n_rev / n_total * 100.0, 2) if n_total > 0 else 0.0,
                "baseline_review_rate_pct": base_cfg.get("review_rate_pct", 0.83),
                "current_hold_rate_pct": round(n_hold / n_total * 100.0, 2) if n_total > 0 else 0.0,
                "baseline_hold_rate_pct": base_cfg.get("hold_rate_pct", 1.28),
                "current_fraud_rate_pct": round(gt_fraud / n_total * 100.0, 2) if has_gt and n_total > 0 else None,
                "baseline_fraud_rate_pct": base_cfg.get("fraud_rate_pct", 1.28),
            },
            "performance_status": {
                "labels_available": has_gt,
                "status_text": "Live Metrics Available" if has_gt else "Performance unavailable — ground-truth labels pending",
            },
        }

    def _empty_report(self) -> dict:
        base_cfg = self.config.get("training_baselines", {})
        return {
            "model_metadata": {
                "active_model": base_cfg.get("model_name", "primary_synthetic_lightgbm"),
                "model_version": base_cfg.get("model_version", "lightgbm-sentinel-v1"),
                "training_date": base_cfg.get("training_date", "2025-06-11"),
                "feature_schema": "sentinelrisk_v1_point_in_time",
                "monitoring_version": self.config.get("monitoring_version", "sentinelrisk-monitoring-v1"),
            },
            "overall_drift_status": "NORMAL",
            "monitored_features": [
                {"feature": "amount", "description": "Transaction Amount", "psi": 0.0, "status": "NORMAL", "mean_value": 0.0},
                {"feature": "cust_velocity_1h", "description": "Customer 1h Velocity", "psi": 0.0, "status": "NORMAL", "mean_value": 0.0},
                {"feature": "cust_amount_ratio", "description": "Customer Spend Ratio", "psi": 0.0, "status": "NORMAL", "mean_value": 0.0},
                {"feature": "risk_score", "description": "Model Calibrated Probability", "psi": 0.0, "status": "NORMAL", "mean_value": 0.0},
            ],
            "operational_distributions": {
                "current_sample_size": 0,
                "current_approval_rate_pct": 0.0,
                "baseline_approval_rate_pct": base_cfg.get("approval_rate_pct", 96.74),
                "current_challenge_rate_pct": 0.0,
                "baseline_challenge_rate_pct": base_cfg.get("challenge_rate_pct", 1.16),
                "current_review_rate_pct": 0.0,
                "baseline_review_rate_pct": base_cfg.get("review_rate_pct", 0.83),
                "current_hold_rate_pct": 0.0,
                "baseline_hold_rate_pct": base_cfg.get("hold_rate_pct", 1.28),
                "current_fraud_rate_pct": None,
                "baseline_fraud_rate_pct": base_cfg.get("fraud_rate_pct", 1.28),
            },
            "performance_status": {
                "labels_available": False,
                "status_text": "Performance unavailable — ground-truth labels pending",
            },
        }

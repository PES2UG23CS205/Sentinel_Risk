"""
SentinelRisk — Deterministic Merchant Anomaly Alerts (Stage 14)

Evaluates merchant profiles and scores to generate deterministic operational risk alerts.
Recommends actions (MONITOR, REVIEW, ESCALATE) while preserving human analyst authority.
"""

from datetime import datetime
from typing import Any
import yaml
from pathlib import Path


class MerchantAlertGenerator:
    """Evaluates merchant metrics against deterministic threshold rules to produce actionable alerts."""

    def __init__(self, config_path: str = "config/merchant_risk.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._alert_counter = 1

    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {
            "alert_thresholds": {
                "fraud_rate_spike_pct": 3.0,
                "velocity_spike_count_1h": 15,
                "risk_score_high_threshold": 0.60,
                "customer_concentration_pct": 50.0,
            }
        }

    def generate_alerts(self, profile: dict, score_data: dict) -> list[dict]:
        """
        Evaluate merchant metrics and return a list of active alerts.
        """
        alerts = []
        m_id = str(profile.get("merchant_id", "UNKNOWN"))
        now_str = profile.get("as_of_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        cfg = self.config.get("alert_thresholds", {})

        fraud_rate = float(profile.get("fraud_rate_pct", 0.0))
        risk_score = float(score_data.get("risk_score", 0.0))
        wm = profile.get("window_metrics", {})
        vol_1h = int(wm.get("1h_transactions", 0))
        cust_conc = float(profile.get("customer_concentration_pct", 0.0))
        trend = profile.get("trend_direction", "STABLE")

        # 1. Fraud Rate Spike Alert
        f_thresh = float(cfg.get("fraud_rate_spike_pct", 3.0))
        if fraud_rate >= f_thresh:
            alerts.append({
                "alert_id": f"MALT-{self._alert_counter:04d}",
                "merchant_id": m_id,
                "timestamp": now_str,
                "alert_type": "FRAUD_RATE_SPIKE",
                "severity": "CRITICAL" if fraud_rate >= 5.0 else "HIGH",
                "reason": f"Merchant fraud rate reached {fraud_rate:.2f}% (exceeds {f_thresh:.1f}% threshold).",
                "recommended_action": "ESCALATE",
                "status": "ACTIVE",
            })
            self._alert_counter += 1

        # 2. Velocity Anomaly Spike
        v_thresh = int(cfg.get("velocity_spike_count_1h", 15))
        if vol_1h >= v_thresh:
            alerts.append({
                "alert_id": f"MALT-{self._alert_counter:04d}",
                "merchant_id": m_id,
                "timestamp": now_str,
                "alert_type": "VELOCITY_SPIKE",
                "severity": "HIGH",
                "reason": f"1-hour transaction volume surged to {vol_1h} authorizations (threshold: {v_thresh}).",
                "recommended_action": "REVIEW",
                "status": "ACTIVE",
            })
            self._alert_counter += 1

        # 3. Overall High Risk Alert
        r_thresh = float(cfg.get("risk_score_high_threshold", 0.60))
        if risk_score >= r_thresh:
            alerts.append({
                "alert_id": f"MALT-{self._alert_counter:04d}",
                "merchant_id": m_id,
                "timestamp": now_str,
                "alert_type": "RISK_SCORE_INCREASE",
                "severity": "HIGH",
                "reason": f"Merchant risk score reached {risk_score:.2f} (High Risk Band).",
                "recommended_action": "REVIEW",
                "status": "ACTIVE",
            })
            self._alert_counter += 1

        # 4. Customer Concentration Anomaly
        c_thresh = float(cfg.get("customer_concentration_pct", 50.0))
        if cust_conc >= c_thresh and profile.get("total_transactions", 0) >= 5:
            alerts.append({
                "alert_id": f"MALT-{self._alert_counter:04d}",
                "merchant_id": m_id,
                "timestamp": now_str,
                "alert_type": "UNUSUAL_CUSTOMER_CONCENTRATION",
                "severity": "MEDIUM",
                "reason": f"Top 2 customers account for {cust_conc:.1f}% of total merchant processing volume.",
                "recommended_action": "MONITOR",
                "status": "ACTIVE",
            })
            self._alert_counter += 1

        # 5. Coordinated Activity / Trend Anomaly
        if trend == "DETERIORATING" and (profile.get("review_rate_pct", 0) + profile.get("hold_rate_pct", 0)) >= 5.0:
            alerts.append({
                "alert_id": f"MALT-{self._alert_counter:04d}",
                "merchant_id": m_id,
                "timestamp": now_str,
                "alert_type": "COORDINATED_ACTIVITY",
                "severity": "HIGH",
                "reason": "Elevated policy intervention rate observed alongside deteriorating risk trajectory.",
                "recommended_action": "REVIEW",
                "status": "ACTIVE",
            })
            self._alert_counter += 1

        return alerts

"""
SentinelRisk — Interpretable Merchant Risk Scorer (Stage 14)

Computes a deterministic, interpretable merchant-level risk score [0.0, 1.0]
with explicit, additive driver attributions.
"""

import yaml
from pathlib import Path
from typing import Any


class MerchantRiskScorer:
    """Calculates weighted merchant risk scores and provides additive component attributions."""

    def __init__(self, config_path: str = "config/merchant_risk.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {
            "scoring_weights": {
                "fraud_rate_weight": 0.25,
                "velocity_anomaly_weight": 0.20,
                "high_risk_density_weight": 0.20,
                "customer_concentration_weight": 0.15,
                "trend_acceleration_weight": 0.20,
            },
            "risk_bands": {"low_max": 0.25, "medium_max": 0.60, "high_min": 0.60},
        }

    def score_merchant(self, profile: dict) -> dict:
        """
        Compute deterministic merchant risk score and additive driver breakdown.
        """
        w = self.config.get("scoring_weights", {})
        w_fraud = float(w.get("fraud_rate_weight", 0.25))
        w_vel = float(w.get("velocity_anomaly_weight", 0.20))
        w_density = float(w.get("high_risk_density_weight", 0.20))
        w_conc = float(w.get("customer_concentration_weight", 0.15))
        w_trend = float(w.get("trend_acceleration_weight", 0.20))

        fraud_rate = float(profile.get("fraud_rate_pct", 0.0))
        wm = profile.get("window_metrics", {})
        vol_1h = float(wm.get("1h_transactions", 0))
        rev_rate = float(profile.get("review_rate_pct", 0.0))
        hold_rate = float(profile.get("hold_rate_pct", 0.0))
        cust_conc = float(profile.get("customer_concentration_pct", 0.0))
        trend = profile.get("trend_direction", "STABLE")

        # 1. Fraud Rate Contribution (Normalized up to 4.0% fraud rate)
        c_fraud = min(w_fraud, (fraud_rate / 4.0) * w_fraud)

        # 2. Velocity Anomaly Contribution (Normalized up to 15 txns/hr)
        c_vel = min(w_vel, (vol_1h / 15.0) * w_vel)

        # 3. High-Risk Density Contribution (Normalized up to 5% review+hold rate)
        c_density = min(w_density, ((rev_rate + hold_rate) / 5.0) * w_density)

        # 4. Customer Concentration Contribution (Normalized up to 60% concentration)
        c_conc = min(w_conc, (cust_conc / 60.0) * w_conc)

        # 5. Trend Acceleration Contribution
        if trend == "DETERIORATING":
            c_trend = w_trend
        elif trend == "STABLE":
            c_trend = w_trend * 0.25
        else:  # IMPROVING
            c_trend = 0.0

        # Total Raw Score
        raw_score = c_fraud + c_vel + c_density + c_conc + c_trend
        final_score = float(min(1.0, max(0.0, round(raw_score, 4))))

        # Determine Risk Band
        bands = self.config.get("risk_bands", {"low_max": 0.25, "medium_max": 0.60})
        if final_score >= bands.get("medium_max", 0.60):
            risk_level = "HIGH"
        elif final_score >= bands.get("low_max", 0.25):
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "merchant_id": profile.get("merchant_id"),
            "risk_score": final_score,
            "risk_level": risk_level,
            "trend_direction": trend,
            "drivers": {
                "fraud_rate_contribution": round(c_fraud, 4),
                "velocity_anomaly_contribution": round(c_vel, 4),
                "high_risk_density_contribution": round(c_density, 4),
                "customer_concentration_contribution": round(c_conc, 4),
                "trend_acceleration_contribution": round(c_trend, 4),
            },
            "driver_explanations": [
                f"Historical fraud rate ({fraud_rate:.2f}%) added +{c_fraud:.2f}",
                f"Recent 1-hour transaction velocity ({int(vol_1h)} txns) added +{c_vel:.2f}",
                f"Policy intervention density ({rev_rate + hold_rate:.1f}%) added +{c_density:.2f}",
                f"Customer volume concentration ({cust_conc:.1f}%) added +{c_conc:.2f}",
                f"Risk trajectory '{trend}' added +{c_trend:.2f}",
            ],
        }

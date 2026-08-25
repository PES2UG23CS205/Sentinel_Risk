"""
SentinelRisk — Deterministic Rules-Only Risk Engine

Evaluates transaction risk features using transparent, interpretable, deterministic rules.
Provides complete explainability for every score and decision without any black-box ML.

Rules:
  1. RULE_CUST_AMOUNT_ANOMALY     : Unusual spending relative to customer's own baseline
  2. RULE_CUST_VELOCITY           : Rapid burst of transactions on a customer account
  3. RULE_DEVICE_NOVELTY_COMPOUND : New unrecognized device paired with abnormal spend
  4. RULE_PI_VELOCITY             : High frequency card testing velocity on payment token
  5. RULE_MERCHANT_ANOMALY        : Unusual order size relative to merchant baseline AOV
  6. RULE_OFF_HOUR_ANOMALY        : Off-hour nighttime execution with large ticket value
"""

import pandas as pd
import numpy as np
from backend.app.policy.config import RuleConfig


class RulesEngine:
    """Deterministic, explainable rules-based risk decision engine."""

    def __init__(self, config: RuleConfig | None = None):
        self.config = config or RuleConfig()

    def evaluate_transaction(self, row: dict) -> dict:
        """
        Evaluate a single transaction record and return score, decision, and explainability report.

        Returns:
            dict containing:
              - rule_score: int
              - decision: 'APPROVE' | 'REVIEW' | 'HOLD'
              - is_flagged: bool (score >= flag_score_threshold)
              - triggered_rules: list of str
              - explanations: list of str
        """
        amount = float(row.get("amount", 0.0))
        cust_is_first_txn = int(row.get("cust_is_first_txn", 0))
        cust_ratio = float(row.get("cust_amount_to_mean_ratio", 1.0))
        vel_1h = int(row.get("velocity_txn_count_1h", 0))
        vel_24h = int(row.get("velocity_txn_count_24h", 0))
        dev_new = int(row.get("device_is_new_for_cust", 0))
        pi_vel_1h = int(row.get("pi_velocity_count_1h", 0))
        merch_ratio = float(row.get("amount_to_merchant_mean_ratio", 1.0))
        is_night = int(row.get("is_night", 0))

        score = 0
        triggered_rules = []
        explanations = []

        # 1. Customer Amount Anomaly
        if cust_is_first_txn == 0 and cust_ratio >= self.config.cust_amount_ratio_threshold:
            score += self.config.weight_cust_amount_anomaly
            rule_name = "RULE_CUST_AMOUNT_ANOMALY"
            triggered_rules.append(rule_name)
            explanations.append(
                f"Transaction amount (INR {amount:.2f}) is {cust_ratio:.1f}x customer historical average "
                f"(threshold: {self.config.cust_amount_ratio_threshold:.1f}x)."
            )

        # 2. Customer Velocity
        if (vel_1h >= self.config.cust_velocity_1h_threshold or
                vel_24h >= self.config.cust_velocity_24h_threshold):
            score += self.config.weight_cust_velocity
            rule_name = "RULE_CUST_VELOCITY"
            triggered_rules.append(rule_name)
            explanations.append(
                f"High customer velocity: {vel_1h} prior txns in 1h (threshold: {self.config.cust_velocity_1h_threshold}) "
                f"or {vel_24h} in 24h (threshold: {self.config.cust_velocity_24h_threshold})."
            )

        # 3. Device Novelty Compound
        if dev_new == 1 and (cust_ratio >= self.config.device_novelty_ratio_threshold or (cust_is_first_txn == 0 and amount >= 5000.0)):
            score += self.config.weight_device_novelty
            rule_name = "RULE_DEVICE_NOVELTY_COMPOUND"
            triggered_rules.append(rule_name)
            explanations.append(
                f"Unrecognized device for customer combined with elevated spending ratio ({cust_ratio:.1f}x)."
            )

        # 4. Payment Instrument Velocity (Card Testing)
        if pi_vel_1h >= self.config.pi_velocity_1h_threshold:
            score += self.config.weight_pi_velocity
            rule_name = "RULE_PI_VELOCITY"
            triggered_rules.append(rule_name)
            explanations.append(
                f"Payment instrument velocity burst: {pi_vel_1h} attempts in 1h "
                f"(threshold: {self.config.pi_velocity_1h_threshold})."
            )

        # 5. Merchant Relative Anomaly
        if merch_ratio >= self.config.merchant_amount_ratio_threshold:
            score += self.config.weight_merchant_anomaly
            rule_name = "RULE_MERCHANT_ANOMALY"
            triggered_rules.append(rule_name)
            explanations.append(
                f"Transaction amount is {merch_ratio:.1f}x merchant baseline average order value "
                f"(threshold: {self.config.merchant_amount_ratio_threshold:.1f}x)."
            )

        # 6. Off-Hour Anomaly
        if is_night == 1 and amount >= self.config.night_amount_threshold:
            score += self.config.weight_off_hour_anomaly
            rule_name = "RULE_OFF_HOUR_ANOMALY"
            triggered_rules.append(rule_name)
            explanations.append(
                f"Off-hour nighttime transaction (00:00-05:59) with high amount INR {amount:.2f} "
                f"(threshold: INR {self.config.night_amount_threshold:.2f})."
            )

        # Decision Mapping
        if score >= self.config.threshold_hold:
            decision = "HOLD"
        elif score >= self.config.threshold_review:
            decision = "REVIEW"
        else:
            decision = "APPROVE"

        is_flagged = score >= self.config.flag_score_threshold

        return {
            "rule_score": score,
            "decision": decision,
            "is_flagged": is_flagged,
            "triggered_rules": triggered_rules,
            "explanations": explanations,
        }

    def evaluate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorized/batch evaluation of rules across an entire dataframe of features.

        Returns:
            df augmented with:
              - rule_1_cust_amount_anomaly (bool)
              - rule_2_cust_velocity (bool)
              - rule_3_device_novelty (bool)
              - rule_4_pi_velocity (bool)
              - rule_5_merchant_anomaly (bool)
              - rule_6_off_hour_anomaly (bool)
              - rule_score (int)
              - is_flagged (bool)
              - decision (str)
        """
        res = df.copy()

        # Rule 1: Customer Amount Anomaly
        r1 = (res["cust_is_first_txn"] == 0) & (res["cust_amount_to_mean_ratio"] >= self.config.cust_amount_ratio_threshold)
        
        # Rule 2: Customer Velocity
        r2 = (res["velocity_txn_count_1h"] >= self.config.cust_velocity_1h_threshold) | (res["velocity_txn_count_24h"] >= self.config.cust_velocity_24h_threshold)

        # Rule 3: Device Novelty Compound
        r3 = (res["device_is_new_for_cust"] == 1) & (
            (res["cust_amount_to_mean_ratio"] >= self.config.device_novelty_ratio_threshold) | 
            ((res["cust_is_first_txn"] == 0) & (res["amount"] >= 5000.0))
        )

        # Rule 4: Payment Instrument Velocity
        r4 = res["pi_velocity_count_1h"] >= self.config.pi_velocity_1h_threshold

        # Rule 5: Merchant Relative Anomaly
        r5 = res["amount_to_merchant_mean_ratio"] >= self.config.merchant_amount_ratio_threshold

        # Rule 6: Off-Hour Anomaly
        r6 = (res["is_night"] == 1) & (res["amount"] >= self.config.night_amount_threshold)

        res["rule_1_cust_amount_anomaly"] = r1
        res["rule_2_cust_velocity"] = r2
        res["rule_3_device_novelty"] = r3
        res["rule_4_pi_velocity"] = r4
        res["rule_5_merchant_anomaly"] = r5
        res["rule_6_off_hour_anomaly"] = r6

        # Score calculation
        score = (
            r1.astype(int) * self.config.weight_cust_amount_anomaly +
            r2.astype(int) * self.config.weight_cust_velocity +
            r3.astype(int) * self.config.weight_device_novelty +
            r4.astype(int) * self.config.weight_pi_velocity +
            r5.astype(int) * self.config.weight_merchant_anomaly +
            r6.astype(int) * self.config.weight_off_hour_anomaly
        )
        res["rule_score"] = score
        res["is_flagged"] = score >= self.config.flag_score_threshold

        # Decision mapping
        conditions = [
            score >= self.config.threshold_hold,
            score >= self.config.threshold_review,
        ]
        choices = ["HOLD", "REVIEW"]
        res["decision"] = np.select(conditions, choices, default="APPROVE")

        return res

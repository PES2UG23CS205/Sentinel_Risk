"""
SentinelRisk — Cost-Sensitive Multi-Signal Policy Engine (Stage 12)

Evaluates ML fraud probability, entity graph ring intelligence, and deterministic
rules under a transparent, auditable, cost-sensitive decision hierarchy.

Decision States:
  - APPROVE: Zero customer friction (Low Risk Baseline)
  - CHALLENGE: Automated Step-Up Verification (Medium / Uncertain Risk)
  - REVIEW: Human Analyst Investigation (High Risk / Coordinated Abuse)
  - HOLD: Immediate Payment Protection (Critical / Severe Fraud Threat)
"""

from pathlib import Path
from typing import Any, Optional

from backend.app.policy.models import (
    DecisionState,
    DecisionRecord,
    PolicyConfig,
)
from backend.app.policy.challenge_catalog import (
    ChallengeRecommendation,
    select_challenge_type,
)


class PolicyEngine:
    """Deterministic, cost-sensitive quad-state policy decision engine."""

    def __init__(
        self,
        config: PolicyConfig | None = None,
        config_path: str | Path | None = None,
        enable_challenge: bool = True,
    ):
        if config is not None:
            self.config = config
        elif config_path is not None:
            self.config = PolicyConfig.from_yaml(config_path)
        else:
            default_yaml = Path("config/policy.yaml")
            if default_yaml.exists():
                self.config = PolicyConfig.from_yaml(default_yaml)
            else:
                self.config = PolicyConfig()
        self.enable_challenge = enable_challenge

    def evaluate(
        self,
        transaction_id: int | str,
        timestamp: str,
        amount: float,
        ml_probability: float,
        graph_ring_score: float = 0.0,
        graph_ring_candidate: int = 0,
        feature_context: dict | None = None,
        rule_signals: list[str] | None = None,
    ) -> DecisionRecord:
        """
        Evaluate multi-signal risk evidence and generate an auditable DecisionRecord.

        Args:
            transaction_id: Unique transaction ID
            timestamp: Transaction timestamp string
            amount: Transaction amount
            ml_probability: LightGBM fraud probability [0.0, 1.0]
            graph_ring_score: Point-in-time entity graph ring score [0.0, 1.0]
            graph_ring_candidate: Binary flag from graph detector (1 or 0)
            feature_context: Point-in-time transaction features (velocities, ratios, etc.)
            rule_signals: Optional list of triggered rule names
        """
        ctx = feature_context or {}
        triggered_rules = list(rule_signals or [])

        pi_vel_1h = int(ctx.get("pi_velocity_count_1h", 0))
        cust_ratio = float(ctx.get("cust_amount_to_mean_ratio", 1.0))
        dev_new = int(ctx.get("device_is_new_for_cust", 0))

        signals_triggered = []
        reasons = []

        # 1. Inspect ML Signal
        if ml_probability >= self.config.ml_thresholds.hold_threshold:
            signals_triggered.append("HIGH_CONFIDENCE_ML_RISK")
            reasons.append(
                f"ML fraud probability ({ml_probability:.3f}) exceeds critical hold threshold ({self.config.ml_thresholds.hold_threshold:.2f})."
            )
        elif ml_probability >= self.config.ml_thresholds.review_threshold:
            signals_triggered.append("HIGH_ML_RISK")
            reasons.append(
                f"ML fraud probability ({ml_probability:.3f}) exceeds manual review threshold ({self.config.ml_thresholds.review_threshold:.2f})."
            )
        elif ml_probability >= self.config.ml_thresholds.challenge_threshold:
            signals_triggered.append("ELEVATED_ML_RISK")
            reasons.append(
                f"ML fraud probability ({ml_probability:.3f}) exceeds step-up challenge threshold ({self.config.ml_thresholds.challenge_threshold:.2f})."
            )

        # 2. Inspect Graph Ring Signal
        if graph_ring_candidate == 1 or graph_ring_score >= self.config.graph_thresholds.ring_score_review:
            if graph_ring_score >= self.config.graph_thresholds.ring_score_hold:
                signals_triggered.append("SEVERE_GRAPH_RING_SYNDICATE")
                reasons.append(
                    f"Entity graph ring score ({graph_ring_score:.2f}) indicates dense multi-account syndicate infrastructure."
                )
            else:
                signals_triggered.append("ELEVATED_GRAPH_RING_SCORE")
                reasons.append(
                    f"Entity graph ring score ({graph_ring_score:.2f}) exceeds syndicate review threshold."
                )

        # 3. Inspect Deterministic Rule Signals
        if pi_vel_1h >= self.config.rule_conditions.severe_card_velocity_1h:
            rule_name = "RULE_SEVERE_PI_VELOCITY_BURST"
            if rule_name not in triggered_rules:
                triggered_rules.append(rule_name)
            signals_triggered.append("SEVERE_PI_VELOCITY")
            reasons.append(
                f"Severe card authorization burst: {pi_vel_1h} transactions on payment token in 1 hour (limit: {self.config.rule_conditions.severe_card_velocity_1h})."
            )
        elif pi_vel_1h >= self.config.rule_conditions.moderate_card_velocity_1h:
            rule_name = "RULE_PI_VELOCITY_ELEVATED"
            if rule_name not in triggered_rules:
                triggered_rules.append(rule_name)
            signals_triggered.append("MODERATE_PI_VELOCITY")
            reasons.append(
                f"Elevated card velocity: {pi_vel_1h} transactions on payment token in 1 hour."
            )

        if cust_ratio >= self.config.rule_conditions.severe_cust_amount_ratio:
            rule_name = "RULE_SEVERE_CUST_AMOUNT_ANOMALY"
            if rule_name not in triggered_rules:
                triggered_rules.append(rule_name)
            signals_triggered.append("SEVERE_AMOUNT_ANOMALY")
            reasons.append(
                f"Extreme spending surge: Amount ({amount:.2f}) is {cust_ratio:.1f}x customer historical mean."
            )
        elif cust_ratio >= self.config.rule_conditions.moderate_cust_amount_ratio:
            rule_name = "RULE_MODERATE_CUST_AMOUNT_ANOMALY"
            if rule_name not in triggered_rules:
                triggered_rules.append(rule_name)
            signals_triggered.append("MODERATE_AMOUNT_ANOMALY")
            reasons.append(
                f"Spending surge: Amount ({amount:.2f}) is {cust_ratio:.1f}x customer historical mean."
            )

        if dev_new == 1:
            signals_triggered.append("NEW_DEVICE_DETECTED")

        # --- Decision Precedence Hierarchy (Stage 12) ---
        decision = DecisionState.APPROVE
        primary_trigger = "LOW_RISK_BASELINE"
        challenge_rec: Optional[ChallengeRecommendation] = None

        # Tier 1: HOLD Precedence (Immediate high-severity intervention)
        if "SEVERE_PI_VELOCITY" in signals_triggered:
            decision = DecisionState.HOLD
            primary_trigger = "SEVERE_PI_VELOCITY"
        elif "HIGH_CONFIDENCE_ML_RISK" in signals_triggered:
            decision = DecisionState.HOLD
            primary_trigger = "HIGH_CONFIDENCE_ML_RISK"
        elif "SEVERE_GRAPH_RING_SYNDICATE" in signals_triggered:
            decision = DecisionState.HOLD
            primary_trigger = "SEVERE_GRAPH_RING_SYNDICATE"
        elif ml_probability >= 0.20 and graph_ring_score >= 0.50 and graph_ring_candidate == 1:
            decision = DecisionState.HOLD
            primary_trigger = "COMPOUND_ML_GRAPH_SYNDICATE"
            reasons.append(
                f"Compound risk: Both ML probability ({ml_probability:.3f}) and graph ring score ({graph_ring_score:.2f}) are elevated."
            )

        # Tier 2: REVIEW Precedence (Complex syndicate or high anomaly requiring human review)
        elif "ELEVATED_GRAPH_RING_SCORE" in signals_triggered:
            decision = DecisionState.REVIEW
            primary_trigger = "ELEVATED_GRAPH_RING_SCORE"
        elif "HIGH_ML_RISK" in signals_triggered:
            decision = DecisionState.REVIEW
            primary_trigger = "HIGH_ML_RISK"
        elif "SEVERE_AMOUNT_ANOMALY" in signals_triggered:
            decision = DecisionState.REVIEW
            primary_trigger = "SEVERE_AMOUNT_ANOMALY"

        # Tier 3: CHALLENGE Precedence (Moderate / Uncertain Risk -> Automated Step-Up)
        elif self.enable_challenge and (
            "ELEVATED_ML_RISK" in signals_triggered
            or "MODERATE_PI_VELOCITY" in signals_triggered
            or "MODERATE_AMOUNT_ANOMALY" in signals_triggered
            or ("NEW_DEVICE_DETECTED" in signals_triggered and cust_ratio >= 2.0)
        ):
            decision = DecisionState.CHALLENGE
            if "ELEVATED_ML_RISK" in signals_triggered:
                primary_trigger = "ELEVATED_ML_RISK"
            elif "MODERATE_PI_VELOCITY" in signals_triggered:
                primary_trigger = "MODERATE_PI_VELOCITY"
            elif "MODERATE_AMOUNT_ANOMALY" in signals_triggered:
                primary_trigger = "MODERATE_AMOUNT_ANOMALY"
            else:
                primary_trigger = "NEW_DEVICE_RISK"

            challenge_rec = select_challenge_type(ctx, signals_triggered, amount)
            reasons.append(
                f"Automated step-up challenge recommended ({challenge_rec.name}): {challenge_rec.reason}"
            )

        # Fallback when challenge is disabled but elevated signals exist
        elif (
            "ELEVATED_ML_RISK" in signals_triggered
            or "MODERATE_PI_VELOCITY" in signals_triggered
            or "MODERATE_AMOUNT_ANOMALY" in signals_triggered
        ):
            decision = DecisionState.REVIEW
            primary_trigger = signals_triggered[0]

        # Tier 4: APPROVE (Normal legitimate frictionless activity)
        else:
            decision = DecisionState.APPROVE
            primary_trigger = "APPROVED_LOW_RISK"
            reasons.append("All risk signals within acceptable baseline thresholds.")

        return DecisionRecord(
            transaction_id=transaction_id,
            timestamp=str(timestamp),
            amount=float(amount),
            ml_probability=float(ml_probability),
            graph_ring_score=float(graph_ring_score),
            graph_ring_candidate=int(graph_ring_candidate),
            triggered_rules=triggered_rules,
            policy_version=self.config.policy_version,
            decision=decision,
            primary_trigger=primary_trigger,
            reasons=reasons,
            signals_triggered=signals_triggered,
            challenge=challenge_rec,
        )

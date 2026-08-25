"""
SentinelRisk — Resilience, Failure Injection & Graceful Degradation

Defines dependency health states and fallback strategies when upstream systems degrade:
  - ML Failure: Fallback to graph intelligence + deterministic velocity rules (ml_status = DEGRADED)
  - Graph Failure: Fallback to ML model + deterministic velocity rules (graph_status = UNAVAILABLE)
  - Policy Failure: Fail-safe conservative intervention (policy_status = FAILED -> REVIEW)
  - Investigation Failure: Retain authoritative Stage 7 decision unchanged (investigation_status = UNAVAILABLE)
"""

from enum import Enum
from dataclasses import dataclass


class DependencyStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class ResilienceConfig:
    simulate_ml_failure: bool = False
    simulate_graph_failure: bool = False
    simulate_policy_failure: bool = False
    simulate_investigation_failure: bool = False


class FallbackPolicyEvaluator:
    """Provides conservative decision fallback when primary components experience outages."""

    @staticmethod
    def evaluate_with_ml_degraded(
        graph_ring_score: float,
        graph_ring_candidate: int,
        feature_context: dict,
    ) -> tuple[str, list[str]]:
        """Fallback when ML model is degraded (ML score missing/failed)."""
        reasons = ["[RESILIENCE] ML service degraded; falling back to graph & velocity perimeter."]
        pi_vel = int(feature_context.get("pi_velocity_count_1h", 0))
        cust_ratio = float(feature_context.get("cust_amount_to_mean_ratio", 1.0))

        if pi_vel >= 5 or (graph_ring_score >= 0.80 and graph_ring_candidate == 1):
            reasons.append("Severe velocity burst or graph syndicate detected in fallback mode.")
            return "HOLD", reasons
        elif pi_vel >= 3 or cust_ratio >= 5.0 or (graph_ring_score >= 0.50 and graph_ring_candidate == 1):
            reasons.append("Elevated risk detected under fallback rules.")
            return "REVIEW", reasons
        else:
            reasons.append("Fallback baseline rules cleared.")
            return "APPROVE", reasons

    @staticmethod
    def evaluate_with_graph_unavailable(
        ml_probability: float,
        feature_context: dict,
    ) -> tuple[str, list[str]]:
        """Fallback when Graph database is unavailable."""
        reasons = ["[RESILIENCE] Graph service unavailable; falling back to ML & velocity perimeter."]
        pi_vel = int(feature_context.get("pi_velocity_count_1h", 0))

        if pi_vel >= 5 or ml_probability >= 0.50:
            reasons.append("Severe ML anomaly or velocity burst detected in fallback mode.")
            return "HOLD", reasons
        elif pi_vel >= 3 or ml_probability >= 0.05:
            reasons.append("Elevated ML risk detected under fallback rules.")
            return "REVIEW", reasons
        else:
            reasons.append("Fallback baseline ML cleared.")
            return "APPROVE", reasons

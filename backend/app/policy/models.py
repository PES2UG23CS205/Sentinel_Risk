"""
SentinelRisk — Policy Engine Data Models

Defines the decision states (APPROVE, REVIEW, HOLD), structured decision records,
and strongly-typed policy configuration data models.
"""

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import yaml


class DecisionState(str, Enum):
    """Quad-state risk decision actions (Stage 12)."""
    APPROVE = "APPROVE"
    CHALLENGE = "CHALLENGE"
    REVIEW = "REVIEW"
    HOLD = "HOLD"


@dataclass
class MLThresholds:
    challenge_threshold: float = 0.05
    review_threshold: float = 0.25
    hold_threshold: float = 0.50


@dataclass
class GraphThresholds:
    ring_score_review: float = 0.50
    ring_score_hold: float = 0.80
    min_ring_customers: int = 3


@dataclass
class RuleConditions:
    severe_card_velocity_1h: int = 5
    moderate_card_velocity_1h: int = 3
    severe_cust_amount_ratio: float = 6.0
    moderate_cust_amount_ratio: float = 4.0


@dataclass
class CostModel:
    false_positive_cost: float = 150.0
    challenge_friction_cost: float = 35.0
    review_cost: float = 50.0
    fraud_loss_multiplier: float = 1.0
    hold_friction_cost: float = 250.0


@dataclass
class OperationalConstraints:
    max_review_rate: float = 0.05
    max_hold_rate: float = 0.02


@dataclass
class PolicyConfig:
    """Strongly-typed policy configuration object loaded from YAML."""
    policy_version: str = "sentinelrisk-policy-v1"
    description: str = "Default multi-signal policy"
    ml_thresholds: MLThresholds = field(default_factory=MLThresholds)
    graph_thresholds: GraphThresholds = field(default_factory=GraphThresholds)
    rule_conditions: RuleConditions = field(default_factory=RuleConditions)
    cost_model: CostModel = field(default_factory=CostModel)
    operational_constraints: OperationalConstraints = field(default_factory=OperationalConstraints)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "PolicyConfig":
        """Load policy configuration from a YAML file."""
        p = Path(yaml_path)
        if not p.exists():
            raise FileNotFoundError(f"Policy config file not found: {yaml_path}")
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyConfig":
        """Construct PolicyConfig from a dictionary."""
        ml_data = data.get("ml_thresholds", {})
        graph_data = data.get("graph_thresholds", {})
        rule_data = data.get("rule_conditions", {})
        cost_data = data.get("cost_model", {})
        ops_data = data.get("operational_constraints", {})

        return cls(
            policy_version=data.get("policy_version", "sentinelrisk-policy-v1"),
            description=data.get("description", ""),
            ml_thresholds=MLThresholds(
                challenge_threshold=float(ml_data.get("challenge_threshold", 0.05)),
                review_threshold=float(ml_data.get("review_threshold", 0.25)),
                hold_threshold=float(ml_data.get("hold_threshold", 0.50)),
            ),
            graph_thresholds=GraphThresholds(
                ring_score_review=float(graph_data.get("ring_score_review", 0.50)),
                ring_score_hold=float(graph_data.get("ring_score_hold", 0.80)),
                min_ring_customers=int(graph_data.get("min_ring_customers", 3)),
            ),
            rule_conditions=RuleConditions(
                severe_card_velocity_1h=int(rule_data.get("severe_card_velocity_1h", 5)),
                moderate_card_velocity_1h=int(rule_data.get("moderate_card_velocity_1h", 3)),
                severe_cust_amount_ratio=float(rule_data.get("severe_cust_amount_ratio", 6.0)),
                moderate_cust_amount_ratio=float(rule_data.get("moderate_cust_amount_ratio", 4.0)),
            ),
            cost_model=CostModel(
                false_positive_cost=float(cost_data.get("false_positive_cost", 150.0)),
                challenge_friction_cost=float(cost_data.get("challenge_friction_cost", 35.0)),
                review_cost=float(cost_data.get("review_cost", 50.0)),
                fraud_loss_multiplier=float(cost_data.get("fraud_loss_multiplier", 1.0)),
                hold_friction_cost=float(cost_data.get("hold_friction_cost", 250.0)),
            ),
            operational_constraints=OperationalConstraints(
                max_review_rate=float(ops_data.get("max_review_rate", 0.05)),
                max_hold_rate=float(ops_data.get("max_hold_rate", 0.02)),
            ),
        )


@dataclass
class DecisionRecord:
    """Structured, immutable audit record for an evaluated transaction."""
    transaction_id: int | str
    timestamp: str
    amount: float
    ml_probability: float
    graph_ring_score: float
    graph_ring_candidate: int
    triggered_rules: list[str]
    policy_version: str
    decision: DecisionState
    primary_trigger: str
    reasons: list[str]
    signals_triggered: list[str]
    challenge: Any | None = None

    @property
    def is_intervention(self) -> bool:
        """True if the policy intercepted the transaction (CHALLENGE, REVIEW, or HOLD)."""
        return self.decision in (DecisionState.CHALLENGE, DecisionState.REVIEW, DecisionState.HOLD)

    @property
    def is_analyst_case(self) -> bool:
        """True if the transaction enters the human analyst review queue."""
        return self.decision in (DecisionState.REVIEW, DecisionState.HOLD)

    def to_dict(self) -> dict:
        """Export to serializable dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "timestamp": str(self.timestamp),
            "amount": self.amount,
            "ml_probability": round(self.ml_probability, 4),
            "graph_ring_score": round(self.graph_ring_score, 4),
            "graph_ring_candidate": self.graph_ring_candidate,
            "triggered_rules": self.triggered_rules,
            "policy_version": self.policy_version,
            "decision": self.decision.value,
            "is_intervention": int(self.is_intervention),
            "is_analyst_case": int(self.is_analyst_case),
            "primary_trigger": self.primary_trigger,
            "reasons": self.reasons,
            "signals_triggered": self.signals_triggered,
            "challenge": self.challenge.to_dict() if hasattr(self.challenge, "to_dict") else self.challenge,
        }

"""
SentinelRisk — Rules-Only Policy Configuration

Defines configurable thresholds, rule weights, decision bands, cost parameters,
and chronological split fractions.
"""

from dataclasses import dataclass, field


@dataclass
class RuleConfig:
    """Configuration for deterministic rules baseline and cost modeling."""

    # --- Rule Activation Thresholds ---
    cust_amount_ratio_threshold: float = 4.0        # Flag if amount >= 4.0x customer average
    cust_velocity_1h_threshold: int = 3             # Flag if >= 3 txns in 1 hour
    cust_velocity_24h_threshold: int = 6            # Flag if >= 6 txns in 24 hours
    device_novelty_ratio_threshold: float = 2.5     # Flag if new device + amount >= 2.5x customer average
    pi_velocity_1h_threshold: int = 3               # Flag if >= 3 txns on card/PI in 1 hour
    merchant_amount_ratio_threshold: float = 5.0    # Flag if amount >= 5.0x merchant baseline AOV
    night_amount_threshold: float = 8000.0          # Flag if night txn (00:00-05:59) and amount >= 8000 INR

    # --- Rule Weights (Points awarded when rule triggers) ---
    weight_cust_amount_anomaly: int = 2
    weight_cust_velocity: int = 2
    weight_device_novelty: int = 2
    weight_pi_velocity: int = 3
    weight_merchant_anomaly: int = 1
    weight_off_hour_anomaly: int = 1

    # --- Risk Bands / Decision Thresholds ---
    # Score < threshold_review -> APPROVE (Low Risk)
    # threshold_review <= Score < threshold_hold -> REVIEW (Medium Risk)
    # Score >= threshold_hold -> HOLD / DECLINE (High Risk)
    threshold_review: float = 3.0
    threshold_hold: float = 5.0

    # Binary flag decision threshold (for binary classification metrics like Precision/Recall)
    flag_score_threshold: float = 3.0

    # --- Business Cost Model (Illustrative Parameters) ---
    # Cost incurred when a legitimate customer transaction is incorrectly flagged / reviewed
    false_positive_cost: float = 150.0  # INR per false positive (customer friction & review overhead)
    # Cost incurred for human triage / manual review
    review_cost: float = 50.0          # INR per reviewed transaction
    # Multiplier on transaction amount lost when fraud is incorrectly approved
    fraud_loss_multiplier: float = 1.0  # 100% of transaction value lost on False Negative

    # --- Temporal Split ---
    train_fraction: float = 0.70
    val_fraction: float = 0.15
    test_fraction: float = 0.15

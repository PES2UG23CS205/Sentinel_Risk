"""
SentinelRisk — Dispute Generator

Generates realistic post-transaction dispute/chargeback records.

Crucial Temporal and Behavioral Properties:
  - Disputes ALWAYS occur with a realistic delay (3 to 45 days) AFTER the transaction.
  - Higher dispute rate on fraudulent transactions (~60%) vs legitimate ones (~0.8%).
  - Diverse dispute reasons (fraud_reported, unauthorized, product_not_received, billing_error).
  - Disputes are post-transaction events and cannot be used as features at transaction time.
"""

import numpy as np
from datetime import timedelta
from simulation.data_generation.config import GenerationConfig


def generate_disputes(
    rng: np.random.Generator,
    config: GenerationConfig,
    transactions: list[dict],
) -> list[dict]:
    """
    Generate synthetic dispute records for transactions.

    Returns:
        list of dispute dicts matching the Dispute ORM schema.
    """
    disputes = []
    dispute_id_counter = 1

    fraud_reasons = ["fraud_reported", "unauthorized_transaction", "card_compromised"]
    legit_reasons = ["product_not_received", "billing_error", "defective_merchandise", "cancelled_recurring"]

    statuses = ["open", "under_review", "resolved", "escalated"]
    status_weights = [0.15, 0.25, 0.55, 0.05]

    for t in transactions:
        # Only captured/successful transactions are disputed in practice
        if t["status"] != "captured":
            continue

        is_fraud = t["is_fraud_ground_truth"]
        prob = config.fraud_dispute_rate if is_fraud else config.legit_dispute_rate

        if rng.random() < prob:
            # Calculate dispute creation delay
            delay_days = rng.uniform(config.dispute_delay_min_days, config.dispute_delay_max_days)
            dispute_time = t["timestamp"] + timedelta(days=float(delay_days))

            # If dispute falls beyond simulation end, clamp or keep within window
            if dispute_time > config.sim_end + timedelta(days=60):
                continue

            reason = str(rng.choice(fraud_reasons)) if is_fraud else str(rng.choice(legit_reasons))
            status = str(rng.choice(statuses, p=status_weights))

            disputes.append({
                "id": dispute_id_counter,
                "transaction_id": t["id"],
                "reason": reason,
                "status": status,
                "created_at": dispute_time,
            })
            dispute_id_counter += 1

    # Sort disputes chronologically by created_at
    disputes.sort(key=lambda d: d["created_at"])

    # Re-index dispute IDs
    for i, d in enumerate(disputes):
        d["id"] = i + 1

    return disputes

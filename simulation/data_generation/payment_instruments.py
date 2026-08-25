"""
SentinelRisk — Payment Instrument Generator

Generates synthetic payment instruments (cards, UPI, wallets, bank accounts).
Security / Compliance:
  - Uses strictly synthetic tokens/identifiers.
  - NEVER generates real PANs, CVVs, expiry dates, or real bank account numbers.
"""

import numpy as np
from datetime import timedelta
from simulation.data_generation.config import GenerationConfig


def generate_payment_instruments(
    rng: np.random.Generator,
    config: GenerationConfig,
    customers: list[dict],
) -> tuple[list[dict], dict[int, list[int]]]:
    """
    Generate payment instruments linked to customers.

    Returns:
        payment_instruments: list of dicts [{"id": int, "customer_id": int, "type": str, "created_at": datetime}]
        customer_pis: dict mapping customer_id -> list of payment_instrument_ids
    """
    pi_types = [t[0] for t in config.pi_types]
    pi_weights = np.array([t[1] for t in config.pi_types])
    pi_weights /= pi_weights.sum()

    payment_instruments = []
    customer_pis: dict[int, list[int]] = {c["id"]: [] for c in customers}
    pi_id_counter = 1

    # Most customers have 1-2 PIs, few have 3
    pi_counts = rng.choice([1, 2, 3], size=len(customers), p=[0.70, 0.25, 0.05])

    for i, cust in enumerate(customers):
        c_id = cust["id"]
        c_created = cust["account_created_at"]
        n_pis = pi_counts[i]

        assigned_types = rng.choice(pi_types, size=n_pis, p=pi_weights)

        for pi_idx in range(n_pis):
            pi_id = pi_id_counter
            pi_id_counter += 1
            pi_type = assigned_types[pi_idx]

            # Payment instrument added at or after account creation
            offset_days = rng.uniform(0, 30) if pi_idx > 0 else rng.uniform(0, 1)
            pi_created = min(config.sim_end, c_created + timedelta(days=float(offset_days)))

            payment_instruments.append({
                "id": pi_id,
                "customer_id": c_id,
                "type": pi_type,
                "created_at": pi_created,
            })
            customer_pis[c_id].append(pi_id)

    return payment_instruments, customer_pis

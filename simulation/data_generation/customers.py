"""
SentinelRisk — Customer Generator

Generates ~40,000 customers with behavioral profiles across 4 segments:
  - low_frequency  (40%): ~1 txn/month
  - regular        (35%): ~4 txn/month
  - high_frequency (15%): ~12 txn/month
  - high_value     (10%): ~3 txn/month at higher amounts

Each customer gets preferred categories, spending range, activity hours,
and preferred days — introducing natural variation so models cannot learn
simplistic rules.
"""

import numpy as np
from datetime import timedelta
from simulation.data_generation.config import GenerationConfig


def generate_customers(
    rng: np.random.Generator,
    config: GenerationConfig,
    merchants: list[dict],
) -> list[dict]:
    """
    Generate customers with behavioral profiles.

    Returns list of dicts with keys:
        id, segment, account_created_at, preferred_categories,
        typical_amount, typical_amount_std, txn_per_month,
        preferred_hour_center, preferred_hour_std,
        preferred_days, amount_multiplier
    """
    segments = [s[0] for s in config.customer_segments]
    seg_weights = np.array([s[1] for s in config.customer_segments])
    seg_weights /= seg_weights.sum()

    seg_txn_mean = {s[0]: s[2] for s in config.customer_segments}
    seg_txn_std = {s[0]: s[3] for s in config.customer_segments}
    seg_amt_mult = {s[0]: s[4] for s in config.customer_segments}

    categories = list({m["category"] for m in merchants})
    sim_days = (config.sim_end - config.sim_start).days

    assigned_segments = rng.choice(segments, size=config.num_customers, p=seg_weights)

    # Account creation: spread across simulation with strong early bias
    creation_days = rng.beta(1.2, 3.0, size=config.num_customers) * sim_days

    customers = []
    for i in range(config.num_customers):
        seg = assigned_segments[i]

        # Preferred categories (1-3 categories)
        n_prefs = rng.integers(1, 4)
        pref_cats = list(rng.choice(categories, size=n_prefs, replace=False))

        # Transaction frequency (Poisson rate per month)
        txn_rate = max(0.2, rng.normal(seg_txn_mean[seg], seg_txn_std[seg]))

        # Spending profile: base from preferred categories × segment multiplier
        # Use lognormal for realistic right-skewed amount distribution
        base_amount = float(rng.lognormal(np.log(1500), 0.6))
        typical_amount = base_amount * seg_amt_mult[seg]
        typical_amount = max(50.0, min(typical_amount, 50000.0))
        amount_std = typical_amount * rng.uniform(0.2, 0.5)

        # Preferred transaction hour (center of activity)
        hour_center = float(rng.choice(
            range(24),
            p=np.array(config.hour_weights) / sum(config.hour_weights),
        ))
        hour_std = rng.uniform(1.5, 4.0)

        # Preferred days (some customers are weekday shoppers, some weekend)
        day_prefs = list(rng.choice(
            range(7),
            size=rng.integers(3, 8),
            replace=False,
            p=np.array(config.day_weights) / sum(config.day_weights),
        ))

        created_at = config.sim_start + timedelta(days=float(creation_days[i]))

        customers.append({
            "id": i + 1,
            "segment": seg,
            "account_created_at": created_at,
            "preferred_categories": pref_cats,
            "typical_amount": round(typical_amount, 2),
            "typical_amount_std": round(amount_std, 2),
            "txn_per_month": round(txn_rate, 2),
            "preferred_hour_center": hour_center,
            "preferred_hour_std": hour_std,
            "preferred_days": sorted(day_prefs),
            "amount_multiplier": seg_amt_mult[seg],
        })

    return customers

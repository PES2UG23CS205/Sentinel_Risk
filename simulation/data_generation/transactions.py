"""
SentinelRisk — Normal Transaction Generator

Generates legitimate transactions according to customer behavioral profiles,
merchant categories, and temporal patterns across a 6-month simulated timeline.

Key features:
  - Chronological simulation day-by-day.
  - Transactions honor customer account creation dates.
  - Category and merchant selection driven by customer preferences.
  - Amount modeling using lognormal distributions with realistic customer-specific
    and merchant-specific bounds.
  - Natural legitimate behavioral variation (occasional high-ticket purchases, bursts).
  - Realistic transaction statuses (captured, failed, cancelled).
"""

import numpy as np
from datetime import datetime, timedelta
from simulation.data_generation.config import GenerationConfig


def generate_normal_transactions(
    rng: np.random.Generator,
    config: GenerationConfig,
    merchants: list[dict],
    customers: list[dict],
    customer_devices: dict[int, list[int]],
    customer_pis: dict[int, list[int]],
) -> list[dict]:
    """
    Generate normal, legitimate transactions across the 6-month simulated window.

    Returns:
        list of transaction dicts matching the Transaction ORM schema.
    """
    # Index merchants by category and build volume-based selection weights
    merchants_by_cat: dict[str, list[dict]] = {}
    merchants_vol_weights: dict[str, np.ndarray] = {}
    all_merchant_ids = [m["id"] for m in merchants]
    all_merchant_vols = np.array([m["expected_daily_transactions"] for m in merchants], dtype=float)
    all_merchant_vols /= all_merchant_vols.sum()

    for m in merchants:
        cat = m["category"]
        merchants_by_cat.setdefault(cat, []).append(m)

    for cat, m_list in merchants_by_cat.items():
        vols = np.array([m["expected_daily_transactions"] for m in m_list], dtype=float)
        vols /= vols.sum()
        merchants_vol_weights[cat] = vols

    # Status distribution
    statuses = [s[0] for s in config.txn_statuses]
    status_weights = np.array([s[1] for s in config.txn_statuses])
    status_weights /= status_weights.sum()

    # Time simulation setup
    start_date = config.sim_start.date()
    end_date = config.sim_end.date()
    total_days = (end_date - start_date).days + 1

    # Target transactions before fraud injection (approx 59,280)
    target_normal_txns = config.target_transactions - int(config.target_transactions * config.fraud_prevalence_target)
    
    # Calculate exact active-weighted expected transactions
    total_expected_txns = 0.0
    for cust in customers:
        c_start = cust["account_created_at"].date()
        if c_start <= end_date:
            active_days = (end_date - max(start_date, c_start)).days + 1
            total_expected_txns += cust["txn_per_month"] * (active_days / 30.0)

    scale_factor = target_normal_txns / max(1.0, total_expected_txns)

    transactions = []
    txn_id_counter = 1

    # Pre-filter customers by active date for efficiency
    # Iterate day by day
    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)
        day_of_week = current_date.weekday()
        day_weight = config.day_weights[day_of_week] * 7.0  # Normalized day multiplier

        # Find customers eligible on this date (account created on or before current_date)
        # To make it performant, we can sample active customers
        # Daily probability for each customer: (txn_per_month / 30.0) * scale_factor * day_weight
        # For ~40k customers, vectorised decision is fast:
        
        # Sample transactions for this day
        for cust in customers:
            if cust["account_created_at"].date() > current_date:
                continue

            # Check if customer prefers this day of week
            pref_day_mult = 1.3 if day_of_week in cust["preferred_days"] else 0.7
            daily_prob = (cust["txn_per_month"] / 30.0) * scale_factor * day_weight * pref_day_mult

            # Draw number of transactions for this customer today (Poisson)
            num_txns = rng.poisson(daily_prob)
            if num_txns == 0:
                continue

            c_id = cust["id"]
            c_devs = customer_devices.get(c_id, [])
            c_pis = customer_pis.get(c_id, [])

            if not c_devs or not c_pis:
                continue

            for _ in range(num_txns):
                # 1. Select merchant (85% preferred category, 15% random category)
                if rng.random() < 0.85 and cust["preferred_categories"]:
                    chosen_cat = rng.choice(cust["preferred_categories"])
                    m_pool = merchants_by_cat[chosen_cat]
                    m_weights = merchants_vol_weights[chosen_cat]
                    merchant = m_pool[rng.choice(len(m_pool), p=m_weights)]
                else:
                    m_idx = rng.choice(len(merchants), p=all_merchant_vols)
                    merchant = merchants[m_idx]

                # 2. Select device (primary 85%, other 15%)
                if len(c_devs) == 1 or rng.random() < 0.85:
                    dev_id = c_devs[0]
                else:
                    dev_id = rng.choice(c_devs[1:])

                # 3. Select payment instrument (primary 80%, other 20%)
                if len(c_pis) == 1 or rng.random() < 0.80:
                    pi_id = c_pis[0]
                else:
                    pi_id = rng.choice(c_pis[1:])

                # 4. Generate transaction timestamp
                # Preferred hour with Gaussian jitter
                hour = int(np.clip(rng.normal(cust["preferred_hour_center"], cust["preferred_hour_std"]), 0, 23))
                minute = int(rng.integers(0, 60))
                second = int(rng.integers(0, 60))
                txn_timestamp = datetime(
                    current_date.year, current_date.month, current_date.day,
                    hour, minute, second,
                    tzinfo=config.sim_start.tzinfo
                )

                # Ensure timestamp is after customer and device/PI creation
                if txn_timestamp < cust["account_created_at"]:
                    txn_timestamp = cust["account_created_at"] + timedelta(minutes=int(rng.integers(5, 120)))

                # 5. Generate amount with natural variation
                # Baseline blend of customer's typical amount and merchant's typical AOV
                blend_mean = (cust["typical_amount"] * 0.6) + (merchant["typical_order_value"] * 0.4)
                
                # 1.5% chance of legitimate high-ticket outlier purchase (e.g. travel, luxury gift, appliance)
                if rng.random() < 0.015:
                    amount = float(rng.uniform(blend_mean * 2.5, blend_mean * 6.0))
                else:
                    amount = float(rng.normal(blend_mean, blend_mean * 0.25))

                amount = max(10.0, round(amount, 2))

                # 6. Status
                status = str(rng.choice(statuses, p=status_weights))

                transactions.append({
                    "id": txn_id_counter,
                    "merchant_id": merchant["id"],
                    "customer_id": c_id,
                    "device_id": dev_id,
                    "payment_instrument_id": pi_id,
                    "amount": amount,
                    "currency": "INR",
                    "timestamp": txn_timestamp,
                    "status": status,
                    "is_fraud": False,
                    "fraud_archetype": "none",
                    "fraud_case_id": None,
                    "is_fraud_ground_truth": False,
                })
                txn_id_counter += 1

    return transactions

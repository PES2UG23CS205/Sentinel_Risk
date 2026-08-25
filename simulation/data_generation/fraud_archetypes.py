"""
SentinelRisk — Fraud Archetypes Generator & Injector

Injects three realistic fraud archetypes with explicit ground truth:
  1. Account Takeover (ATO):
     - Established customer compromised via a new suspicious device.
     - Burst of high-value transactions in rapid succession, often at off-hours.
  2. Card Testing / Velocity Fraud:
     - Rapid-fire low-value transactions (₹10–₹100) within minutes.
     - Concentrated on high-throughput or digital merchants with high failure rate.
  3. Coordinated Abuse Ring:
     - Multiple synthetic accounts sharing common devices and payment instruments.
     - Coordinated timing targeting specific merchant clusters.

Also implements realistic label noise while preserving the pristine ground truth.
"""

import numpy as np
from datetime import datetime, timedelta
from simulation.data_generation.config import GenerationConfig


def inject_fraud_archetypes(
    rng: np.random.Generator,
    config: GenerationConfig,
    transactions: list[dict],
    merchants: list[dict],
    customers: list[dict],
    devices: list[dict],
    payment_instruments: list[dict],
    customer_devices: dict[int, list[int]],
    customer_pis: dict[int, list[int]],
) -> list[dict]:
    """
    Inject Account Takeover, Card Testing, and Coordinated Ring fraud scenarios.

    Returns:
        Augmented transactions list with ground truth and archetype metadata.
    """
    start_id = max(t["id"] for t in transactions) + 1 if transactions else 1
    device_id_counter = max(d["id"] for d in devices) + 1 if devices else 1
    pi_id_counter = max(p["id"] for p in payment_instruments) + 1 if payment_instruments else 1

    merchants_by_cat: dict[str, list[dict]] = {}
    for m in merchants:
        merchants_by_cat.setdefault(m["category"], []).append(m)

    all_high_value_merchants = merchants_by_cat.get("electronics", []) + merchants_by_cat.get("travel", [])
    if not all_high_value_merchants:
        all_high_value_merchants = merchants

    digital_merchants = merchants_by_cat.get("digital_services", []) + merchants_by_cat.get("entertainment", [])
    if not digital_merchants:
        digital_merchants = merchants

    # Map customer transactions to find established customers
    cust_txns: dict[int, list[dict]] = {}
    for t in transactions:
        cust_txns.setdefault(t["customer_id"], []).append(t)

    established_cust_ids = [c_id for c_id, t_list in cust_txns.items() if len(t_list) >= 2]
    if len(established_cust_ids) < config.ato_cases:
        established_cust_ids = [c["id"] for c in customers]

    # -------------------------------------------------------------------------
    # 1. ARCHETYPE 1: ACCOUNT TAKEOVER (ATO)
    # -------------------------------------------------------------------------
    ato_victim_ids = rng.choice(established_cust_ids, size=min(config.ato_cases, len(established_cust_ids)), replace=False)
    
    for case_idx, victim_id in enumerate(ato_victim_ids):
        case_id = f"ATO_{case_idx + 1:03d}"
        victim = customers[victim_id - 1]
        victim_txns = cust_txns.get(victim_id, [])

        # Pick a point in time after the victim has transacted legitimately
        if victim_txns:
            latest_legit_time = max(t["timestamp"] for t in victim_txns)
            ato_start_time = latest_legit_time + timedelta(days=float(rng.uniform(5, 30)))
        else:
            ato_start_time = victim["account_created_at"] + timedelta(days=float(rng.uniform(10, 60)))

        ato_start_time = min(config.sim_end - timedelta(days=5), ato_start_time)

        # Attacker introduces a new device
        attacker_dev_id = device_id_counter
        device_id_counter += 1
        devices.append({
            "id": attacker_dev_id,
            "created_at": ato_start_time - timedelta(minutes=int(rng.integers(10, 120))),
        })
        customer_devices[victim_id].append(attacker_dev_id)

        # Uses victim's existing PI or injects a compromised card
        victim_pis = customer_pis.get(victim_id, [])
        pi_id = victim_pis[0] if victim_pis else 1

        # Burst of 3-8 high-value transactions
        num_burst = int(rng.integers(config.ato_burst_min, config.ato_burst_max + 1))
        curr_time = ato_start_time

        for _ in range(num_burst):
            target_merchant = all_high_value_merchants[rng.choice(len(all_high_value_merchants))]
            amount = float(round(victim["typical_amount"] * config.ato_amount_multiplier * rng.uniform(0.8, 1.4), 2))
            amount = max(3000.0, min(amount, 80000.0))

            # Status: mostly captured, some fail due to security checks
            status = "captured" if rng.random() < 0.80 else "failed"

            transactions.append({
                "id": start_id,
                "merchant_id": target_merchant["id"],
                "customer_id": victim_id,
                "device_id": attacker_dev_id,
                "payment_instrument_id": pi_id,
                "amount": amount,
                "currency": "INR",
                "timestamp": curr_time,
                "status": status,
                "is_fraud": True,
                "fraud_archetype": "account_takeover",
                "fraud_case_id": case_id,
                "is_fraud_ground_truth": True,
            })
            start_id += 1
            curr_time += timedelta(minutes=int(rng.integers(5, 180)))

    # -------------------------------------------------------------------------
    # 2. ARCHETYPE 2: CARD TESTING / VELOCITY FRAUD
    # -------------------------------------------------------------------------
    ct_customers = rng.choice(customers, size=config.ct_cases, replace=False)

    for case_idx, cust in enumerate(ct_customers):
        case_id = f"CT_{case_idx + 1:03d}"
        c_id = cust["id"]

        # Base time
        ct_time = cust["account_created_at"] + timedelta(days=float(rng.uniform(2, 60)))
        ct_time = min(config.sim_end - timedelta(days=2), ct_time)

        # Attacker uses or creates payment instrument for testing
        test_pi_id = pi_id_counter
        pi_id_counter += 1
        payment_instruments.append({
            "id": test_pi_id,
            "customer_id": c_id,
            "type": "card",
            "created_at": ct_time - timedelta(minutes=5),
        })
        customer_pis[c_id].append(test_pi_id)

        c_devs = customer_devices.get(c_id, [1])
        dev_id = c_devs[0]

        # Target 1-2 digital/low-friction merchants
        n_targets = rng.choice([1, 2], p=[0.7, 0.3])
        target_merchants = [digital_merchants[i] for i in rng.choice(len(digital_merchants), size=n_targets, replace=False)]

        # Rapid burst of 10-30 small transactions within minutes
        num_burst = int(rng.integers(config.ct_burst_min, config.ct_burst_max + 1))
        curr_time = ct_time

        for _ in range(num_burst):
            m = target_merchants[rng.choice(len(target_merchants))]
            amount = float(round(rng.uniform(10.0, config.ct_small_amount_max), 2))
            
            # Card testing typically has high decline/failure rate
            status = "failed" if rng.random() < 0.45 else "captured"

            transactions.append({
                "id": start_id,
                "merchant_id": m["id"],
                "customer_id": c_id,
                "device_id": dev_id,
                "payment_instrument_id": test_pi_id,
                "amount": amount,
                "currency": "INR",
                "timestamp": curr_time,
                "status": status,
                "is_fraud": True,
                "fraud_archetype": "card_testing",
                "fraud_case_id": case_id,
                "is_fraud_ground_truth": True,
            })
            start_id += 1
            # Interval of 20 to 120 seconds between card testing attempts
            curr_time += timedelta(seconds=int(rng.integers(20, 120)))

    # -------------------------------------------------------------------------
    # 3. ARCHETYPE 3: COORDINATED ABUSE RINGS
    # -------------------------------------------------------------------------
    available_cust_pool = [c["id"] for c in customers if c["id"] not in ato_victim_ids]

    for ring_idx in range(config.ring_count):
        case_id = f"RING_{ring_idx + 1:03d}"
        
        # Ring sizes: small (3), medium (5), large (8)
        ring_size = int(rng.choice([3, 5, 8], p=[0.5, 0.35, 0.15]))
        ring_member_ids = list(rng.choice(available_cust_pool, size=ring_size, replace=False))

        # Shared infrastructure: 1 or 2 syndicate devices
        syndicate_dev_id = device_id_counter
        device_id_counter += 1
        ring_start_time = config.sim_start + timedelta(days=float(rng.uniform(30, 150)))
        
        devices.append({
            "id": syndicate_dev_id,
            "created_at": ring_start_time - timedelta(days=1),
        })

        # Shared syndicate payment instrument
        syndicate_pi_id = pi_id_counter
        pi_id_counter += 1
        payment_instruments.append({
            "id": syndicate_pi_id,
            "customer_id": ring_member_ids[0],
            "type": "card",
            "created_at": ring_start_time - timedelta(days=1),
        })

        # Link shared device and PI to all ring members
        for m_id in ring_member_ids:
            customer_devices[m_id].append(syndicate_dev_id)
            customer_pis[m_id].append(syndicate_pi_id)

        # Ring targets 2-4 specific merchants
        n_ring_merchants = rng.integers(2, 5)
        ring_merchants = [merchants[i] for i in rng.choice(len(merchants), size=n_ring_merchants, replace=False)]

        # Generate coordinated transactions across ring members in a narrow window (1-3 days)
        for m_id in ring_member_ids:
            for _ in range(config.ring_txn_per_member):
                m = ring_merchants[rng.choice(len(ring_merchants))]
                t_time = ring_start_time + timedelta(
                    hours=float(rng.uniform(0, 48)),
                    minutes=int(rng.integers(0, 60)),
                    seconds=int(rng.integers(0, 60))
                )
                t_time = min(config.sim_end, t_time)

                amount = float(round(rng.uniform(2500.0, 15000.0), 2))
                status = "captured" if rng.random() < 0.85 else "failed"

                transactions.append({
                    "id": start_id,
                    "merchant_id": m["id"],
                    "customer_id": m_id,
                    "device_id": syndicate_dev_id,
                    "payment_instrument_id": syndicate_pi_id,
                    "amount": amount,
                    "currency": "INR",
                    "timestamp": t_time,
                    "status": status,
                    "is_fraud": True,
                    "fraud_archetype": "coordinated_ring",
                    "fraud_case_id": case_id,
                    "is_fraud_ground_truth": True,
                })
                start_id += 1

    # -------------------------------------------------------------------------
    # 4. LABEL NOISE INJECTION
    # -------------------------------------------------------------------------
    # Realistic operational datasets suffer from noisy labels (false disputes, delayed reviews)
    # We introduce label noise into `is_fraud` while strictly preserving `is_fraud_ground_truth`
    num_noisy = int(len(transactions) * config.label_noise_rate)
    noise_indices = rng.choice(len(transactions), size=num_noisy, replace=False)

    for idx in noise_indices:
        t = transactions[idx]
        # Flip observed label
        t["is_fraud"] = not t["is_fraud_ground_truth"]

    # Re-sort all transactions chronologically to ensure strict temporal causality
    transactions.sort(key=lambda t: t["timestamp"])

    # Re-assign clean sequential IDs after chronological sorting
    for i, t in enumerate(transactions):
        t["id"] = i + 1

    return transactions

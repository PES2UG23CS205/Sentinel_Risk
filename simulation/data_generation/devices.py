"""
SentinelRisk — Device Generator

Generates devices and establishes customer-device relationships.
Crucially:
  - Most customers use 1-2 devices.
  - A small fraction of devices (~2%) are legitimately shared across 2-3 customers
    (e.g., family members, shared tablets/workplace PCs).
  - This ensures that 'shared device' is not a trivial deterministic shortcut for fraud.
"""

import numpy as np
from datetime import timedelta
from simulation.data_generation.config import GenerationConfig


def generate_devices(
    rng: np.random.Generator,
    config: GenerationConfig,
    customers: list[dict],
) -> tuple[list[dict], dict[int, list[int]], dict[int, list[int]]]:
    """
    Generate devices and customer-device mappings.

    Returns:
        devices: list of dicts [{"id": int, "created_at": datetime}]
        customer_devices: dict mapping customer_id -> list of device_ids
        device_customers: dict mapping device_id -> list of customer_ids
    """
    num_customers = len(customers)
    device_id_counter = 1
    devices = []
    customer_devices: dict[int, list[int]] = {c["id"]: [] for c in customers}
    device_customers: dict[int, list[int]] = {}

    # Step 1: Assign primary devices for all customers
    # Distribution of devices per customer: 1 (75%), 2 (20%), 3 (5%)
    device_counts = rng.choice([1, 2, 3], size=num_customers, p=[0.75, 0.20, 0.05])

    for i, cust in enumerate(customers):
        c_id = cust["id"]
        c_created = cust["account_created_at"]
        n_devs = device_counts[i]

        for dev_idx in range(n_devs):
            dev_id = device_id_counter
            device_id_counter += 1

            # Device creation timestamp is on or slightly before/after account creation
            offset_hours = rng.uniform(-48, 720) if dev_idx > 0 else rng.uniform(-24, 2)
            dev_created = max(config.sim_start, c_created + timedelta(hours=float(offset_hours)))
            dev_created = min(config.sim_end, dev_created)

            devices.append({
                "id": dev_id,
                "created_at": dev_created,
            })
            customer_devices[c_id].append(dev_id)
            device_customers[dev_id] = [c_id]

    # Step 2: Inject legitimate shared devices (~2% of devices shared by 2-3 customers)
    num_shared_devices = int(len(devices) * config.legitimate_shared_device_rate)
    if num_shared_devices > 0:
        shared_dev_indices = rng.choice(len(devices), size=num_shared_devices, replace=False)
        all_customer_ids = [c["id"] for c in customers]

        for dev_idx in shared_dev_indices:
            shared_dev = devices[dev_idx]
            dev_id = shared_dev["id"]
            owner_id = device_customers[dev_id][0]

            # Pick 1 or 2 additional legitimate sharing customers
            num_additional = rng.choice([1, 2], p=[0.8, 0.2])
            additional_custs = rng.choice(all_customer_ids, size=num_additional, replace=False)

            for add_c_id in additional_custs:
                if add_c_id != owner_id and dev_id not in customer_devices[add_c_id]:
                    customer_devices[add_c_id].append(dev_id)
                    device_customers[dev_id].append(add_c_id)

    return devices, customer_devices, device_customers

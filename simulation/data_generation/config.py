"""
SentinelRisk — Data Generation Configuration

All generation parameters are defined here in a single dataclass.
The generator uses this config to produce deterministic, reproducible
synthetic data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class GenerationConfig:
    """Central configuration for the synthetic data generator."""

    # --- Reproducibility ---
    seed: int = 42
    dataset_version: str = "v1"

    # --- Simulated Time Window ---
    sim_start: datetime = field(
        default_factory=lambda: datetime(2025, 1, 1, tzinfo=timezone.utc)
    )
    sim_end: datetime = field(
        default_factory=lambda: datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    )

    # --- Entity Counts ---
    num_merchants: int = 1500
    num_customers: int = 40000
    target_transactions: int = 60000

    # --- Merchant Categories ---
    # (category, weight, avg_order_value, order_value_std, daily_txn_base)
    merchant_categories: list = field(default_factory=lambda: [
        ("electronics",      0.08,  8500.0,  4000.0,   8),
        ("fashion",          0.12,  2200.0,  1200.0,  15),
        ("grocery",          0.15,   650.0,   350.0,  40),
        ("food_delivery",    0.14,   450.0,   200.0,  50),
        ("travel",           0.06, 12000.0,  8000.0,   5),
        ("education",        0.07,  3500.0,  2500.0,  10),
        ("digital_services", 0.13,   500.0,   300.0,  30),
        ("health",           0.08,  1800.0,  1000.0,  12),
        ("home",             0.09,  4500.0,  3000.0,  10),
        ("entertainment",    0.08,   800.0,   500.0,  20),
    ])

    # --- Merchant Tiers ---
    # (tier_name, weight, volume_multiplier)
    merchant_tiers: list = field(default_factory=lambda: [
        ("small",  0.50, 0.3),
        ("medium", 0.35, 1.0),
        ("large",  0.15, 3.0),
    ])

    # --- Customer Segments ---
    # (segment, weight, txn_per_month_mean, txn_per_month_std, amount_multiplier)
    customer_segments: list = field(default_factory=lambda: [
        ("low_frequency",   0.40,  1.0, 0.5, 0.8),
        ("regular",         0.35,  4.0, 1.5, 1.0),
        ("high_frequency",  0.15, 12.0, 4.0, 1.0),
        ("high_value",      0.10,  3.0, 1.5, 3.0),
    ])

    # --- Payment Instrument Types ---
    # (type, weight)
    pi_types: list = field(default_factory=lambda: [
        ("card",         0.60),
        ("upi",          0.25),
        ("wallet",       0.10),
        ("bank_account", 0.05),
    ])

    # --- Transaction Statuses ---
    # (status, weight)
    txn_statuses: list = field(default_factory=lambda: [
        ("captured",  0.92),
        ("failed",    0.05),
        ("cancelled", 0.03),
    ])

    # --- Devices ---
    devices_per_customer_mean: float = 1.3
    legitimate_shared_device_rate: float = 0.02  # 2% of devices shared by family

    # --- Fraud Parameters ---
    fraud_prevalence_target: float = 0.012  # 1.2%
    fraud_prevalence_min: float = 0.010
    fraud_prevalence_max: float = 0.015

    # Account Takeover
    ato_cases: int = 30
    ato_burst_min: int = 3
    ato_burst_max: int = 6
    ato_amount_multiplier: float = 3.0

    # Card Testing
    ct_cases: int = 25
    ct_burst_min: int = 12
    ct_burst_max: int = 18
    ct_small_amount_max: float = 100.0

    # Coordinated Rings
    ring_count: int = 15
    ring_size_min: int = 3
    ring_size_max: int = 6
    ring_txn_per_member: int = 3

    # --- Label Noise ---
    label_noise_rate: float = 0.02  # 2%

    # --- Disputes ---
    fraud_dispute_rate: float = 0.60    # 60% of fraud txns get disputed
    legit_dispute_rate: float = 0.008   # 0.8% of legit txns get disputed
    dispute_delay_min_days: int = 3
    dispute_delay_max_days: int = 45

    # --- Hour-of-day distribution (weights for hours 0-23) ---
    # Reflects typical Indian payment patterns
    hour_weights: list = field(default_factory=lambda: [
        0.01, 0.005, 0.003, 0.002, 0.002, 0.005,  # 0-5 AM
        0.01, 0.03,  0.05,  0.07,  0.08,  0.09,    # 6-11 AM
        0.08, 0.07,  0.06,  0.05,  0.06,  0.07,    # 12-5 PM
        0.08, 0.09,  0.08,  0.06,  0.04,  0.02,    # 6-11 PM
    ])

    # --- Day-of-week weights (Mon=0 ... Sun=6) ---
    day_weights: list = field(default_factory=lambda: [
        0.15, 0.15, 0.14, 0.14, 0.16, 0.14, 0.12,
    ])

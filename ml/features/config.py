"""
SentinelRisk — Feature Engineering Configuration

Defines point-in-time window sizes, cold-start sentinels, categorical encodings,
and feature store output paths.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FeatureConfig:
    """Configuration parameters for point-in-time feature engineering."""

    # --- Rolling Velocity Window Durations (seconds) ---
    window_1h_seconds: int = 3600
    window_24h_seconds: int = 86400
    window_7d_seconds: int = 604800

    # --- Cold-Start Sentinels & Defaults ---
    sentinel_days_since_last_txn: float = -1.0
    default_amount_to_mean_ratio: float = 1.0
    default_amount_zscore: float = 0.0
    default_decline_rate: float = 0.0

    # --- Night / Off-Hour Windows ---
    night_start_hour: int = 0
    night_end_hour: int = 5  # 00:00 to 05:59

    # --- Output Paths ---
    output_dir: str = "data/features"
    output_features_filename: str = "transaction_features.csv"
    output_metadata_filename: str = "feature_metadata.json"

    # --- Categorical Encodings ---
    merchant_categories: list = field(default_factory=lambda: [
        "digital_services", "education", "electronics", "entertainment",
        "fashion", "food_delivery", "grocery", "health", "home", "travel"
    ])

    payment_instrument_types: list = field(default_factory=lambda: [
        "bank_account", "card", "upi", "wallet"
    ])

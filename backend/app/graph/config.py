"""
SentinelRisk — Entity Graph Configuration

Defines configurable thresholds, weights, and legitimate sharing limits for
graph construction, ego-network clustering, and coordinated abuse ring scoring.
"""

from dataclasses import dataclass, field


@dataclass
class GraphConfig:
    """Configuration for entity graph construction and ring detection."""

    # --- Ring Detection Criteria ---
    min_ring_customers: int = 3               # Minimum distinct customer accounts to form a ring
    min_shared_devices: int = 1               # Minimum shared devices linking customers
    min_shared_payment_instruments: int = 1   # Minimum shared payment instruments linking customers
    temporal_burst_window_hours: float = 72.0 # Concentrated attack activity timespan
    legitimate_device_sharing_cap: int = 2    # Cap for legitimate household / family sharing

    # --- Ring Scoring Weights (Normalized to 1.0) ---
    weight_shared_device: float = 0.35        # Penalty for dense multi-customer device sharing
    weight_shared_pi: float = 0.35            # Penalty for multi-customer card token sharing
    weight_customer_scale: float = 0.15       # Penalty scaling with number of connected accounts
    weight_temporal_burst: float = 0.15       # Penalty for concentrated short-timespan execution

    # Decision threshold for binary ring classification
    ring_score_threshold: float = 0.50

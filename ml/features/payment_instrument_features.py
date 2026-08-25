"""
SentinelRisk — Point-in-Time Payment Instrument Feature Extractor

Computes payment instrument history and velocity strictly using transactions observed
BEFORE timestamp T:
  - Total transactions on instrument
  - Distinct customers and distinct merchants previously associated with instrument
  - PI velocity (1h, 24h activity) — critical for Card Testing detection
  - Instrument age in days
"""

from collections import deque
from datetime import datetime
from ml.features.config import FeatureConfig


class PaymentInstrumentHistoryState:
    """Maintains running statistics and velocity for a payment instrument."""

    def __init__(self, pi_id: int, created_at: datetime):
        self.pi_id = pi_id
        self.created_at = created_at

        self.txn_count: int = 0
        self.seen_customers: set[int] = set()
        self.seen_merchants: set[int] = set()
        self.first_seen_time: datetime | None = None
        self.recent_txns: deque[float] = deque()

    def compute_features(self, ts: datetime, config: FeatureConfig) -> dict:
        """
        Compute payment instrument features for an incoming transaction at timestamp ts.
        """
        ts_sec = ts.timestamp()

        # PI age in days
        first_time = self.first_seen_time or self.created_at
        age_seconds = max(0.0, (ts - first_time).total_seconds())
        pi_age_days = round(age_seconds / 86400.0, 2)

        # Evict timestamps older than 24h (max velocity window needed for PI)
        cutoff_24h = ts_sec - config.window_24h_seconds
        while self.recent_txns and self.recent_txns[0] < cutoff_24h:
            self.recent_txns.popleft()

        cutoff_1h = ts_sec - config.window_1h_seconds
        cnt_1h = sum(1 for t in self.recent_txns if t >= cutoff_1h)
        cnt_24h = len(self.recent_txns)

        return {
            "pi_txn_count_prev": self.txn_count,
            "pi_distinct_cust_prev": len(self.seen_customers),
            "pi_distinct_merchants_prev": len(self.seen_merchants),
            "pi_velocity_count_1h": cnt_1h,
            "pi_velocity_count_24h": cnt_24h,
            "pi_age_days": pi_age_days,
        }

    def update(self, customer_id: int, merchant_id: int, ts: datetime):
        """Record payment instrument usage AFTER scoring."""
        self.txn_count += 1
        self.seen_customers.add(customer_id)
        self.seen_merchants.add(merchant_id)
        if self.first_seen_time is None:
            self.first_seen_time = ts
        self.recent_txns.append(ts.timestamp())

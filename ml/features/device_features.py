"""
SentinelRisk — Point-in-Time Device Feature Extractor

Computes device history, cross-customer device sharing, and customer-device affinity strictly
using transactions observed BEFORE timestamp T:
  - Total transactions on device
  - Distinct customers and distinct merchants previously seen on device
  - Device velocity (24h, 7d activity)
  - device_is_new_for_cust: 1 if customer is using this device for the first time
"""

from collections import deque
from datetime import datetime
from ml.features.config import FeatureConfig


class DeviceHistoryState:
    """Maintains running statistics and sharing history for a device."""

    def __init__(self, device_id: int, created_at: datetime):
        self.device_id = device_id
        self.created_at = created_at

        self.txn_count: int = 0
        self.seen_customers: set[int] = set()
        self.seen_merchants: set[int] = set()
        self.first_seen_time: datetime | None = None
        self.recent_txns: deque[float] = deque()

    def compute_features(self, customer_id: int, ts: datetime, config: FeatureConfig) -> dict:
        """
        Compute device features for an incoming transaction from customer_id at time ts.
        """
        ts_sec = ts.timestamp()

        # Device age in days
        first_time = self.first_seen_time or self.created_at
        age_seconds = max(0.0, (ts - first_time).total_seconds())
        device_age_days = round(age_seconds / 86400.0, 2)

        # Evict timestamps older than 7 days
        cutoff_7d = ts_sec - config.window_7d_seconds
        while self.recent_txns and self.recent_txns[0] < cutoff_7d:
            self.recent_txns.popleft()

        cutoff_24h = ts_sec - config.window_24h_seconds
        cnt_24h = sum(1 for t in self.recent_txns if t >= cutoff_24h)
        cnt_7d = len(self.recent_txns)

        # Has this customer used this device before?
        is_new_for_cust = 1 if customer_id not in self.seen_customers else 0

        return {
            "device_txn_count_prev": self.txn_count,
            "device_distinct_cust_prev": len(self.seen_customers),
            "device_distinct_merchants_prev": len(self.seen_merchants),
            "device_velocity_count_24h": cnt_24h,
            "device_velocity_count_7d": cnt_7d,
            "device_is_new_for_cust": is_new_for_cust,
            "device_age_days": device_age_days,
        }

    def update(self, customer_id: int, merchant_id: int, ts: datetime):
        """Record device usage AFTER scoring."""
        self.txn_count += 1
        self.seen_customers.add(customer_id)
        self.seen_merchants.add(merchant_id)
        if self.first_seen_time is None:
            self.first_seen_time = ts
        self.recent_txns.append(ts.timestamp())

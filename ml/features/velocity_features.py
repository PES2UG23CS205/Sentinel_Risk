"""
SentinelRisk — Point-in-Time Velocity Feature Extractor

Computes rolling trailing-window velocity features strictly in [T - delta, T):
  - 1-Hour: count and amount sum
  - 24-Hour: count and amount sum
  - 7-Day: count and amount sum

The current transaction at timestamp T is NEVER included in the rolling window.
"""

from collections import deque
from datetime import datetime
from ml.features.config import FeatureConfig


class CustomerVelocityState:
    """Maintains a sliding window of recent transactions for a customer."""

    def __init__(self, customer_id: int):
        self.customer_id = customer_id
        # Queue of tuples: (timestamp_epoch_sec: float, amount: float)
        self.history: deque[tuple[float, float]] = deque()

    def compute_features(self, ts: datetime, config: FeatureConfig) -> dict:
        """
        Compute velocity features for an incoming transaction at timestamp ts
        prior to recording the current transaction.
        """
        ts_sec = ts.timestamp()

        # Evict transactions older than 7 days (the maximum window)
        cutoff_7d = ts_sec - config.window_7d_seconds
        while self.history and self.history[0][0] < cutoff_7d:
            self.history.popleft()

        cutoff_1h = ts_sec - config.window_1h_seconds
        cutoff_24h = ts_sec - config.window_24h_seconds

        cnt_1h = 0
        sum_1h = 0.0
        cnt_24h = 0
        sum_24h = 0.0
        cnt_7d = len(self.history)
        sum_7d = 0.0

        # Scan the queue (which contains only <= 7d history, typically very few items per customer)
        for t_time, t_amt in self.history:
            sum_7d += t_amt
            if t_time >= cutoff_24h:
                cnt_24h += 1
                sum_24h += t_amt
            if t_time >= cutoff_1h:
                cnt_1h += 1
                sum_1h += t_amt

        return {
            "velocity_txn_count_1h": cnt_1h,
            "velocity_amount_sum_1h": round(sum_1h, 2),
            "velocity_txn_count_24h": cnt_24h,
            "velocity_amount_sum_24h": round(sum_24h, 2),
            "velocity_txn_count_7d": cnt_7d,
            "velocity_amount_sum_7d": round(sum_7d, 2),
        }

    def update(self, ts: datetime, amount: float):
        """Append the current transaction to history AFTER scoring."""
        self.history.append((ts.timestamp(), amount))

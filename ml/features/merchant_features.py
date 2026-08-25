"""
SentinelRisk — Point-in-Time Merchant Feature Extractor

Computes merchant historical behavior and merchant-relative amount anomalies strictly
using transactions observed BEFORE timestamp T:
  - Merchant account age
  - Historical transaction volume, AOV (mean), standard deviation, decline rate
  - Merchant velocity (1h, 24h, 7d activity)
  - Transaction amount deviation relative to merchant's baseline AOV
"""

import math
from collections import deque
from datetime import datetime
from ml.features.config import FeatureConfig


class MerchantHistoryState:
    """Maintains running statistics and short-term sliding window for a merchant."""

    def __init__(self, merchant_id: int, created_at: datetime, typical_order_value: float = 1000.0):
        self.merchant_id = merchant_id
        self.created_at = created_at
        self.typical_order_value = typical_order_value

        # Cumulative running stats strictly before current transaction
        self.txn_count: int = 0
        self.amount_sum: float = 0.0
        self.amount_sq_sum: float = 0.0
        self.decline_count: int = 0

        # Queue of transaction timestamps (in epoch seconds) for velocity
        self.recent_txns: deque[float] = deque()

    def compute_features(self, amount: float, ts: datetime, config: FeatureConfig) -> dict:
        """
        Compute merchant features prior to recording the current transaction.
        """
        ts_sec = ts.timestamp()

        # Merchant age in days
        age_seconds = max(0.0, (ts - self.created_at).total_seconds())
        merchant_age_days = round(age_seconds / 86400.0, 2)

        # Evict timestamps older than 7 days
        cutoff_7d = ts_sec - config.window_7d_seconds
        while self.recent_txns and self.recent_txns[0] < cutoff_7d:
            self.recent_txns.popleft()

        cutoff_1h = ts_sec - config.window_1h_seconds
        cutoff_24h = ts_sec - config.window_24h_seconds

        cnt_1h = sum(1 for t in self.recent_txns if t >= cutoff_1h)
        cnt_24h = sum(1 for t in self.recent_txns if t >= cutoff_24h)
        cnt_7d = len(self.recent_txns)

        if self.txn_count == 0:
            merchant_amount_mean_prev = round(self.typical_order_value, 2)
            merchant_amount_std_prev = 0.0
            merchant_decline_rate_prev = 0.0
        else:
            merchant_amount_mean_prev = round(self.amount_sum / self.txn_count, 2)
            if self.txn_count >= 2:
                var = max(0.0, (self.amount_sq_sum - (self.amount_sum ** 2 / self.txn_count)) / (self.txn_count - 1))
                merchant_amount_std_prev = round(math.sqrt(var), 2)
            else:
                merchant_amount_std_prev = 0.0
            merchant_decline_rate_prev = round(self.decline_count / self.txn_count, 4)

        # Merchant-relative amount ratio
        denom = max(1.0, merchant_amount_mean_prev)
        amount_to_merchant_mean_ratio = round(amount / denom, 4)

        return {
            "merchant_age_days": merchant_age_days,
            "merchant_txn_count_prev": self.txn_count,
            "merchant_amount_mean_prev": merchant_amount_mean_prev,
            "merchant_amount_std_prev": merchant_amount_std_prev,
            "merchant_decline_rate_prev": merchant_decline_rate_prev,
            "merchant_velocity_txn_count_1h": cnt_1h,
            "merchant_velocity_txn_count_24h": cnt_24h,
            "merchant_velocity_txn_count_7d": cnt_7d,
            "amount_to_merchant_mean_ratio": amount_to_merchant_mean_ratio,
        }

    def update(self, amount: float, ts: datetime, status: str):
        """Update merchant historical state AFTER scoring."""
        self.txn_count += 1
        self.amount_sum += amount
        self.amount_sq_sum += amount * amount
        if status in ("failed", "cancelled"):
            self.decline_count += 1
        self.recent_txns.append(ts.timestamp())

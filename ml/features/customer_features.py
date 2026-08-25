"""
SentinelRisk — Point-in-Time Customer Feature Extractor

Computes customer historical metrics strictly using transactions observed
BEFORE the current transaction timestamp T:
  - Account age in days
  - Historical transaction count, sum, mean, standard deviation, max
  - Days since previous transaction
  - Amount deviation (ratio to mean, Z-score)
  - First-transaction indicator and historical decline rate
"""

import math
from datetime import datetime
from ml.features.config import FeatureConfig


class CustomerHistoryState:
    """Maintains running historical statistics for a customer."""

    def __init__(self, customer_id: int, account_created_at: datetime, typical_amount: float = 1000.0):
        self.customer_id = customer_id
        self.account_created_at = account_created_at
        self.typical_amount = typical_amount

        # Running stats strictly before current transaction
        self.txn_count: int = 0
        self.amount_sum: float = 0.0
        self.amount_sq_sum: float = 0.0
        self.amount_max: float = 0.0
        self.decline_count: int = 0
        self.last_txn_time: datetime | None = None

    def compute_features(self, amount: float, ts: datetime, config: FeatureConfig) -> dict:
        """
        Compute point-in-time features for the incoming transaction at time ts
        WITHOUT mutating internal state yet.
        """
        # Account age in days at authorization time
        age_seconds = max(0.0, (ts - self.account_created_at).total_seconds())
        cust_age_days = round(age_seconds / 86400.0, 2)

        # First transaction / Cold-start
        is_first_txn = 1 if self.txn_count == 0 else 0

        if self.txn_count == 0:
            cust_amount_mean_prev = round(self.typical_amount, 2)
            cust_amount_std_prev = 0.0
            cust_amount_max_prev = 0.0
            cust_amount_sum_prev = 0.0
            cust_days_since_last_txn = config.sentinel_days_since_last_txn
            cust_amount_to_mean_ratio = config.default_amount_to_mean_ratio
            cust_amount_zscore = config.default_amount_zscore
            cust_decline_rate_prev = config.default_decline_rate
        else:
            cust_amount_sum_prev = round(self.amount_sum, 2)
            cust_amount_mean_prev = round(self.amount_sum / self.txn_count, 2)
            cust_amount_max_prev = round(self.amount_max, 2)

            # Sample variance: (sum_sq - (sum^2 / n)) / (n - 1)
            if self.txn_count >= 2:
                variance = max(0.0, (self.amount_sq_sum - (self.amount_sum ** 2 / self.txn_count)) / (self.txn_count - 1))
                cust_amount_std_prev = round(math.sqrt(variance), 2)
            else:
                cust_amount_std_prev = 0.0

            # Days since last transaction
            if self.last_txn_time is not None:
                diff_sec = max(0.0, (ts - self.last_txn_time).total_seconds())
                cust_days_since_last_txn = round(diff_sec / 86400.0, 6)
            else:
                cust_days_since_last_txn = config.sentinel_days_since_last_txn

            # Amount deviation ratio
            denom = max(1.0, cust_amount_mean_prev)
            cust_amount_to_mean_ratio = round(amount / denom, 4)

            # Amount Z-score
            if self.txn_count >= 2 and cust_amount_std_prev > 0.01:
                cust_amount_zscore = round((amount - cust_amount_mean_prev) / cust_amount_std_prev, 4)
            else:
                cust_amount_zscore = config.default_amount_zscore

            # Historical decline rate
            cust_decline_rate_prev = round(self.decline_count / self.txn_count, 4)

        return {
            "cust_age_days": cust_age_days,
            "cust_txn_count_prev": self.txn_count,
            "cust_amount_sum_prev": cust_amount_sum_prev,
            "cust_amount_mean_prev": cust_amount_mean_prev,
            "cust_amount_std_prev": cust_amount_std_prev,
            "cust_amount_max_prev": cust_amount_max_prev,
            "cust_days_since_last_txn": cust_days_since_last_txn,
            "cust_amount_to_mean_ratio": cust_amount_to_mean_ratio,
            "cust_amount_zscore": cust_amount_zscore,
            "cust_is_first_txn": is_first_txn,
            "cust_decline_rate_prev": cust_decline_rate_prev,
        }

    def update(self, amount: float, ts: datetime, status: str):
        """
        Update internal state AFTER the transaction at time ts has been scored.
        """
        self.txn_count += 1
        self.amount_sum += amount
        self.amount_sq_sum += amount * amount
        if amount > self.amount_max:
            self.amount_max = amount
        if status in ("failed", "cancelled"):
            self.decline_count += 1
        self.last_txn_time = ts

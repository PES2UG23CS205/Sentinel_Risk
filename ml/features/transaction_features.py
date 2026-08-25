"""
SentinelRisk — Intrinsic Transaction Feature Extractor

Computes instant / intrinsic transaction properties without looking at history:
  - amount, amount_log
  - hour_of_day, day_of_week, is_weekend, is_night
  - categorical encodings for merchant_category and payment_instrument_type
"""

import math
from datetime import datetime
from ml.features.config import FeatureConfig


def extract_transaction_features(
    amount: float,
    ts: datetime,
    merchant: dict,
    pi: dict,
    config: FeatureConfig,
) -> dict:
    """
    Extract static and timestamp-derived intrinsic features for a single transaction.

    Returns:
        dict of feature name -> float / int value
    """
    amount_val = float(amount)
    amount_log = math.log(amount_val + 1.0)

    hour = ts.hour
    day_of_week = ts.weekday()
    is_weekend = 1 if day_of_week in (5, 6) else 0
    is_night = 1 if config.night_start_hour <= hour <= config.night_end_hour else 0

    category = merchant.get("category", "other")
    pi_type = pi.get("type", "other")

    cat_idx = config.merchant_categories.index(category) if category in config.merchant_categories else -1
    pi_type_idx = config.payment_instrument_types.index(pi_type) if pi_type in config.payment_instrument_types else -1

    return {
        "amount": round(amount_val, 2),
        "amount_log": round(amount_log, 4),
        "hour_of_day": hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_night": is_night,
        "merchant_category_idx": cat_idx,
        "pi_type_idx": pi_type_idx,
    }

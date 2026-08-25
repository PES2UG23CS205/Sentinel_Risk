"""
SentinelRisk — Point-in-Time Feature Builder for External Dataset (Fraud Detection Handbook)

Extracts point-in-time safe (t < T) behavioral features from the Fraud Detection Handbook dataset.
Uses ONLY information legitimately available at transaction authorization time:
  - Transaction amount & log amount
  - Temporal features (hour, day of week, weekend, night)
  - Customer historical velocity (1h, 24h, 7d)
  - Customer spending baseline (mean, std, max, ratio, z-score)
  - Terminal / Merchant historical velocity (1h, 24h, 7d)
  - Terminal average ticket size and customer terminal novelty

Explicitly DOES NOT invent device fingerprints, card tokens, or synthetic graph edges.
"""

import math
from collections import defaultdict, deque
from datetime import datetime
from typing import Any
import numpy as np
import pandas as pd

EXTERNAL_FEATURE_NAMES = [
    "amount",
    "amount_log",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_night",
    "cust_txn_count_prev",
    "cust_velocity_1h",
    "cust_velocity_24h",
    "cust_velocity_7d",
    "cust_amount_sum_prev",
    "cust_amount_mean_prev",
    "cust_amount_std_prev",
    "cust_amount_max_prev",
    "cust_amount_ratio",
    "cust_amount_zscore",
    "terminal_txn_count_prev",
    "terminal_velocity_1h",
    "terminal_velocity_24h",
    "terminal_velocity_7d",
    "terminal_amount_mean_prev",
    "terminal_amount_ratio",
    "terminal_unique_cust_prev",
    "is_new_terminal_for_cust",
]


class ExternalFeatureBuilder:
    """
    Point-in-time feature extraction for Fraud Detection Handbook transactions.
    Can be used for offline batch dataset transformation or online real-time stream processing.
    """

    def __init__(self):
        # Customer history: customer_id -> deque of (unix_time_sec, amount, terminal_id)
        self.customer_history: dict[Any, deque] = defaultdict(deque)
        # Running customer stats: customer_id -> [count, sum_amount, sum_sq_amount, max_amount]
        self.customer_stats: dict[Any, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
        # Terminal history: terminal_id -> deque of (unix_time_sec, amount, customer_id)
        self.terminal_history: dict[Any, deque] = defaultdict(deque)
        # Running terminal stats: terminal_id -> [count, sum_amount]
        self.terminal_stats: dict[Any, list[float]] = defaultdict(lambda: [0.0, 0.0])
        # Set of unique customers seen per terminal: terminal_id -> set(customer_id)
        self.terminal_customers: dict[Any, set[Any]] = defaultdict(set)
        # Customer terminals seen: customer_id -> set(terminal_id)
        self.customer_terminals: dict[Any, set[Any]] = defaultdict(set)

    def reset(self):
        """Reset all in-memory entity history state."""
        self.customer_history.clear()
        self.customer_stats.clear()
        self.terminal_history.clear()
        self.terminal_stats.clear()
        self.terminal_customers.clear()
        self.customer_terminals.clear()

    def extract_single(
        self,
        transaction_id: Any,
        timestamp: datetime | str,
        amount: float,
        customer_id: Any,
        terminal_id: Any,
        tx_time_seconds: int | None = None,
        update_state: bool = True,
    ) -> dict[str, float]:
        """
        Extract features for a single transaction strictly at t < T.
        If update_state=True, updates internal state after feature extraction.
        """
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", ""))
            except Exception:
                dt = datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")
        else:
            dt = timestamp

        if tx_time_seconds is None:
            t_sec = int(dt.timestamp())
        else:
            t_sec = int(tx_time_seconds)

        amt = float(amount)
        amt_log = float(math.log(max(0.0, amt) + 1.0))
        hour = int(dt.hour)
        dow = int(dt.weekday())
        is_weekend = 1.0 if dow in (5, 6) else 0.0
        is_night = 1.0 if 0 <= hour <= 5 else 0.0

        # --- 1. Customer History Features (strictly t < T) ---
        c_stats = self.customer_stats[customer_id]
        c_count = int(c_stats[0])

        if c_count == 0:
            c_v1h = 0.0
            c_v24h = 0.0
            c_v7d = 0.0
            c_sum = 0.0
            c_mean = amt
            c_std = 0.0
            c_max = amt
            c_ratio = 1.0
            c_zscore = 0.0
            is_new_term = 1.0
        else:
            c_hist = self.customer_history[customer_id]
            c_v1h = 0.0
            c_v24h = 0.0
            c_v7d = 0.0
            # Scan in reverse; break early when older than 7 days (604,800s)
            for (pt, _, _) in reversed(c_hist):
                diff = t_sec - pt
                if diff < 0:
                    continue  # Ignore any future events strictly
                if diff <= 3600:
                    c_v1h += 1.0
                    c_v24h += 1.0
                    c_v7d += 1.0
                elif diff <= 86400:
                    c_v24h += 1.0
                    c_v7d += 1.0
                elif diff <= 604800:
                    c_v7d += 1.0
                else:
                    break  # All earlier transactions are > 7 days old

            c_sum = c_stats[1]
            c_mean = c_sum / c_count
            variance = max(0.0, (c_stats[2] / c_count) - (c_mean ** 2))
            c_std = math.sqrt(variance)
            c_max = c_stats[3]
            c_ratio = amt / max(1.0, c_mean)
            c_zscore = (amt - c_mean) / c_std if c_std > 1e-4 else 0.0
            is_new_term = 0.0 if terminal_id in self.customer_terminals[customer_id] else 1.0

        # --- 2. Terminal History Features (strictly t < T) ---
        t_stats = self.terminal_stats[terminal_id]
        t_count = int(t_stats[0])

        if t_count == 0:
            t_v1h = 0.0
            t_v24h = 0.0
            t_v7d = 0.0
            t_mean = amt
            t_ratio = 1.0
            t_uniq_cust = 0.0
        else:
            t_hist = self.terminal_history[terminal_id]
            t_v1h = 0.0
            t_v24h = 0.0
            t_v7d = 0.0
            for (pt, _, _) in reversed(t_hist):
                diff = t_sec - pt
                if diff < 0:
                    continue
                if diff <= 3600:
                    t_v1h += 1.0
                    t_v24h += 1.0
                    t_v7d += 1.0
                elif diff <= 86400:
                    t_v24h += 1.0
                    t_v7d += 1.0
                elif diff <= 604800:
                    t_v7d += 1.0
                else:
                    break

            t_mean = t_stats[1] / t_count
            t_ratio = amt / max(1.0, t_mean)
            t_uniq_cust = float(len(self.terminal_customers[terminal_id]))

        features = {
            "amount": amt,
            "amount_log": amt_log,
            "hour_of_day": float(hour),
            "day_of_week": float(dow),
            "is_weekend": is_weekend,
            "is_night": is_night,
            "cust_txn_count_prev": float(c_count),
            "cust_velocity_1h": c_v1h,
            "cust_velocity_24h": c_v24h,
            "cust_velocity_7d": c_v7d,
            "cust_amount_sum_prev": c_sum,
            "cust_amount_mean_prev": c_mean,
            "cust_amount_std_prev": c_std,
            "cust_amount_max_prev": c_max,
            "cust_amount_ratio": c_ratio,
            "cust_amount_zscore": c_zscore,
            "terminal_txn_count_prev": float(t_count),
            "terminal_velocity_1h": t_v1h,
            "terminal_velocity_24h": t_v24h,
            "terminal_velocity_7d": t_v7d,
            "terminal_amount_mean_prev": t_mean,
            "terminal_amount_ratio": t_ratio,
            "terminal_unique_cust_prev": t_uniq_cust,
            "is_new_terminal_for_cust": is_new_term,
        }

        # --- 3. Update State (Strictly after feature computation) ---
        if update_state:
            # Update customer state
            c_stats[0] += 1.0
            c_stats[1] += amt
            c_stats[2] += amt ** 2
            c_stats[3] = max(c_stats[3], amt) if c_count > 0 else amt
            self.customer_history[customer_id].append((t_sec, amt, terminal_id))
            self.customer_terminals[customer_id].add(terminal_id)

            # Update terminal state
            t_stats[0] += 1.0
            t_stats[1] += amt
            self.terminal_history[terminal_id].append((t_sec, amt, customer_id))
            self.terminal_customers[terminal_id].add(customer_id)

        return features

    def transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sequentially transform a chronologically sorted DataFrame into feature vectors.
        Strictly guarantees temporal point-in-time correctness without future leakage.
        """
        df_sorted = df.sort_values(by=["TX_DATETIME", "TRANSACTION_ID"]).reset_index(drop=True)
        n = len(df_sorted)

        # Pre-extract numpy columns for ultra-fast iteration
        dts = pd.to_datetime(df_sorted["TX_DATETIME"])
        hours = dts.dt.hour.to_numpy(dtype=np.float32)
        dows = dts.dt.dayofweek.to_numpy(dtype=np.float32)
        is_weekends = np.where((dows == 5) | (dows == 6), 1.0, 0.0).astype(np.float32)
        is_nights = np.where((hours >= 0) & (hours <= 5), 1.0, 0.0).astype(np.float32)

        amts = df_sorted["TX_AMOUNT"].to_numpy(dtype=np.float64)
        c_ids = df_sorted["CUSTOMER_ID"].to_numpy()
        term_ids = df_sorted["TERMINAL_ID"].to_numpy()

        if "TX_TIME_SECONDS" in df_sorted.columns:
            tx_secs = df_sorted["TX_TIME_SECONDS"].to_numpy(dtype=np.int64)
        else:
            tx_secs = (dts.astype("int64") // 10**9).to_numpy()

        # Pre-allocate numpy feature matrix: n rows x 24 columns
        matrix = np.zeros((n, len(EXTERNAL_FEATURE_NAMES)), dtype=np.float32)

        c_hist = self.customer_history
        c_stats = self.customer_stats
        c_terms = self.customer_terminals
        t_hist = self.terminal_history
        t_stats = self.terminal_stats
        t_custs = self.terminal_customers

        for i in range(n):
            amt = amts[i]
            amt_log = math.log(amt + 1.0) if amt > 0 else 0.0
            t_sec = tx_secs[i]
            c_id = c_ids[i]
            term_id = term_ids[i]

            # 1. Customer point-in-time features (t < T)
            c_stat = c_stats[c_id]
            c_count = int(c_stat[0])

            if c_count == 0:
                c_v1h = c_v24h = c_v7d = c_sum = 0.0
                c_mean = c_max = amt
                c_std = c_zscore = 0.0
                c_ratio = is_new_term = 1.0
            else:
                c_queue = c_hist[c_id]
                c_v1h = c_v24h = c_v7d = 0.0
                for (pt, _, _) in reversed(c_queue):
                    diff = t_sec - pt
                    if diff <= 3600:
                        c_v1h += 1.0
                        c_v24h += 1.0
                        c_v7d += 1.0
                    elif diff <= 86400:
                        c_v24h += 1.0
                        c_v7d += 1.0
                    elif diff <= 604800:
                        c_v7d += 1.0
                    else:
                        break

                c_sum = c_stat[1]
                c_mean = c_sum / c_count
                var = max(0.0, (c_stat[2] / c_count) - (c_mean ** 2))
                c_std = math.sqrt(var)
                c_max = c_stat[3]
                c_ratio = amt / max(1.0, c_mean)
                c_zscore = (amt - c_mean) / c_std if c_std > 1e-4 else 0.0
                is_new_term = 0.0 if term_id in c_terms[c_id] else 1.0

            # 2. Terminal point-in-time features (t < T)
            t_stat = t_stats[term_id]
            t_count = int(t_stat[0])

            if t_count == 0:
                t_v1h = t_v24h = t_v7d = t_uniq_cust = 0.0
                t_mean = amt
                t_ratio = 1.0
            else:
                t_queue = t_hist[term_id]
                t_v1h = t_v24h = t_v7d = 0.0
                for (pt, _, _) in reversed(t_queue):
                    diff = t_sec - pt
                    if diff <= 3600:
                        t_v1h += 1.0
                        t_v24h += 1.0
                        t_v7d += 1.0
                    elif diff <= 86400:
                        t_v24h += 1.0
                        t_v7d += 1.0
                    elif diff <= 604800:
                        t_v7d += 1.0
                    else:
                        break

                t_mean = t_stat[1] / t_count
                t_ratio = amt / max(1.0, t_mean)
                t_uniq_cust = float(len(t_custs[term_id]))

            # Populate row
            matrix[i, 0] = amt
            matrix[i, 1] = amt_log
            matrix[i, 2] = hours[i]
            matrix[i, 3] = dows[i]
            matrix[i, 4] = is_weekends[i]
            matrix[i, 5] = is_nights[i]
            matrix[i, 6] = float(c_count)
            matrix[i, 7] = c_v1h
            matrix[i, 8] = c_v24h
            matrix[i, 9] = c_v7d
            matrix[i, 10] = c_sum
            matrix[i, 11] = c_mean
            matrix[i, 12] = c_std
            matrix[i, 13] = c_max
            matrix[i, 14] = c_ratio
            matrix[i, 15] = c_zscore
            matrix[i, 16] = float(t_count)
            matrix[i, 17] = t_v1h
            matrix[i, 18] = t_v24h
            matrix[i, 19] = t_v7d
            matrix[i, 20] = t_mean
            matrix[i, 21] = t_ratio
            matrix[i, 22] = t_uniq_cust
            matrix[i, 23] = is_new_term

            # Update state (strictly after feature calculation)
            c_stat[0] += 1.0
            c_stat[1] += amt
            c_stat[2] += amt ** 2
            c_stat[3] = max(c_stat[3], amt) if c_count > 0 else amt
            c_hist[c_id].append((t_sec, amt, term_id))
            c_terms[c_id].add(term_id)

            t_stat[0] += 1.0
            t_stat[1] += amt
            t_hist[term_id].append((t_sec, amt, c_id))
            t_custs[term_id].add(c_id)

        return pd.DataFrame(matrix, columns=EXTERNAL_FEATURE_NAMES)

"""
SentinelRisk — Master Point-in-Time Feature Engineering Pipeline

Executes high-performance O(N) chronological stateful feature extraction across all transactions.
Enforces strict point-in-time causality: every feature is computed as-of strictly BEFORE
the transaction state is recorded.
"""

import json
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from ml.features.config import FeatureConfig
from ml.features.transaction_features import extract_transaction_features
from ml.features.customer_features import CustomerHistoryState
from ml.features.velocity_features import CustomerVelocityState
from ml.features.merchant_features import MerchantHistoryState
from ml.features.device_features import DeviceHistoryState
from ml.features.payment_instrument_features import PaymentInstrumentHistoryState


class FeaturePipeline:
    """Master Point-in-Time Feature Pipeline."""

    def __init__(self, config: FeatureConfig | None = None):
        self.config = config or FeatureConfig()

    def process_dataset(
        self,
        merchants: list[dict],
        customers: list[dict],
        devices: list[dict],
        payment_instruments: list[dict],
        transactions: list[dict],
    ) -> pd.DataFrame:
        """
        Execute chronological single-pass feature extraction over all transactions.

        Returns:
            pd.DataFrame containing feature columns and target label metadata.
        """
        start_time = time.time()

        # Step 1: Build entity lookup dictionaries
        merchant_map = {m["id"]: m for m in merchants}
        cust_map = {c["id"]: c for c in customers}
        device_map = {d["id"]: d for d in devices}
        pi_map = {p["id"]: p for p in payment_instruments}

        # Step 2: Initialize entity state trackers
        cust_states: dict[int, CustomerHistoryState] = {
            c["id"]: CustomerHistoryState(
                customer_id=c["id"],
                account_created_at=self._parse_datetime(c["account_created_at"]),
                typical_amount=float(c.get("typical_amount", 1000.0)),
            )
            for c in customers
        }
        cust_velocity: dict[int, CustomerVelocityState] = {
            c["id"]: CustomerVelocityState(customer_id=c["id"])
            for c in customers
        }
        merchant_states: dict[int, MerchantHistoryState] = {
            m["id"]: MerchantHistoryState(
                merchant_id=m["id"],
                created_at=self._parse_datetime(m["created_at"]),
                typical_order_value=float(m.get("typical_order_value", 1000.0)),
            )
            for m in merchants
        }
        device_states: dict[int, DeviceHistoryState] = {
            d["id"]: DeviceHistoryState(
                device_id=d["id"],
                created_at=self._parse_datetime(d["created_at"]),
            )
            for d in devices
        }
        pi_states: dict[int, PaymentInstrumentHistoryState] = {
            p["id"]: PaymentInstrumentHistoryState(
                pi_id=p["id"],
                created_at=self._parse_datetime(p["created_at"]),
            )
            for p in payment_instruments
        }

        # Step 3: Ensure transactions are strictly sorted by timestamp
        sorted_txns = sorted(transactions, key=lambda t: self._parse_datetime(t["timestamp"]))

        feature_records = []

        # Step 4: Chronological single-pass extraction
        for txn in sorted_txns:
            txn_id = int(txn["id"])
            m_id = int(txn["merchant_id"])
            c_id = int(txn["customer_id"])
            d_id = int(txn["device_id"]) if txn.get("device_id") else None
            pi_id = int(txn["payment_instrument_id"]) if txn.get("payment_instrument_id") else None
            amount = float(txn["amount"])
            status = str(txn.get("status", "captured"))
            ts = self._parse_datetime(txn["timestamp"])

            # Entity references
            merchant = merchant_map.get(m_id, {})
            cust = cust_map.get(c_id, {})
            pi = pi_map.get(pi_id, {}) if pi_id else {}

            # --- A. Compute Features (as-of strictly BEFORE T) ---
            txn_feats = extract_transaction_features(amount, ts, merchant, pi, self.config)

            # Customer features
            c_state = cust_states.get(c_id)
            if c_state is None:
                c_state = CustomerHistoryState(c_id, ts, amount)
                cust_states[c_id] = c_state
            cust_feats = c_state.compute_features(amount, ts, self.config)

            # Velocity features
            c_vel = cust_velocity.get(c_id)
            if c_vel is None:
                c_vel = CustomerVelocityState(c_id)
                cust_velocity[c_id] = c_vel
            vel_feats = c_vel.compute_features(ts, self.config)

            # Merchant features
            m_state = merchant_states.get(m_id)
            if m_state is None:
                m_state = MerchantHistoryState(m_id, ts, amount)
                merchant_states[m_id] = m_state
            merch_feats = m_state.compute_features(amount, ts, self.config)

            # Device features
            if d_id and d_id in device_states:
                dev_feats = device_states[d_id].compute_features(c_id, ts, self.config)
            else:
                dev_feats = {
                    "device_txn_count_prev": 0,
                    "device_distinct_cust_prev": 0,
                    "device_distinct_merchants_prev": 0,
                    "device_velocity_count_24h": 0,
                    "device_velocity_count_7d": 0,
                    "device_is_new_for_cust": 1,
                    "device_age_days": 0.0,
                }

            # Payment instrument features
            if pi_id and pi_id in pi_states:
                pi_feats = pi_states[pi_id].compute_features(ts, self.config)
            else:
                pi_feats = {
                    "pi_txn_count_prev": 0,
                    "pi_distinct_cust_prev": 0,
                    "pi_distinct_merchants_prev": 0,
                    "pi_velocity_count_1h": 0,
                    "pi_velocity_count_24h": 0,
                    "pi_age_days": 0.0,
                }

            # Combine all features for this transaction
            record = {
                "transaction_id": txn_id,
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "merchant_id": m_id,
                "customer_id": c_id,
                "device_id": d_id or -1,
                "payment_instrument_id": pi_id or -1,
                **txn_feats,
                **cust_feats,
                **vel_feats,
                **merch_feats,
                **dev_feats,
                **pi_feats,
                # Target Labels (strictly separated for evaluation and training)
                "is_fraud": bool(txn.get("is_fraud", False)),
                "is_fraud_ground_truth": bool(txn.get("is_fraud_ground_truth", False)),
                "fraud_archetype": str(txn.get("fraud_archetype", "none")),
                "fraud_case_id": str(txn.get("fraud_case_id") or ""),
            }
            feature_records.append(record)

            # --- B. Update State Trackers AFTER feature computation ---
            c_state.update(amount, ts, status)
            c_vel.update(ts, amount)
            m_state.update(amount, ts, status)
            if d_id and d_id in device_states:
                device_states[d_id].update(c_id, m_id, ts)
            if pi_id and pi_id in pi_states:
                pi_states[pi_id].update(c_id, m_id, ts)

        df = pd.DataFrame(feature_records)
        elapsed = time.time() - start_time
        print(f"[OK] Processed {len(df):,} transactions in {elapsed:.2f}s ({len(df)/max(0.01, elapsed):.1f} txns/sec)")

        return df

    def export(self, df: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
        """Export features dataframe and metadata JSON."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        features_path = out_path / self.config.output_features_filename
        meta_path = out_path / self.config.output_metadata_filename

        # Export CSV
        df.to_csv(features_path, index=False)

        # Feature columns list (excluding IDs, timestamps, and target labels)
        excluded_cols = {
            "transaction_id", "timestamp", "merchant_id", "customer_id",
            "device_id", "payment_instrument_id", "is_fraud",
            "is_fraud_ground_truth", "fraud_archetype", "fraud_case_id"
        }
        feature_cols = [c for c in df.columns if c not in excluded_cols]

        metadata = {
            "total_transactions": len(df),
            "num_features": len(feature_cols),
            "feature_columns": feature_cols,
            "feature_categories": {
                "transaction_features": [
                    "amount", "amount_log", "hour_of_day", "day_of_week",
                    "is_weekend", "is_night", "merchant_category_idx", "pi_type_idx"
                ],
                "customer_features": [
                    "cust_age_days", "cust_txn_count_prev", "cust_amount_sum_prev",
                    "cust_amount_mean_prev", "cust_amount_std_prev", "cust_amount_max_prev",
                    "cust_days_since_last_txn", "cust_amount_to_mean_ratio", "cust_amount_zscore",
                    "cust_is_first_txn", "cust_decline_rate_prev"
                ],
                "velocity_features": [
                    "velocity_txn_count_1h", "velocity_amount_sum_1h",
                    "velocity_txn_count_24h", "velocity_amount_sum_24h",
                    "velocity_txn_count_7d", "velocity_amount_sum_7d"
                ],
                "merchant_features": [
                    "merchant_age_days", "merchant_txn_count_prev", "merchant_amount_mean_prev",
                    "merchant_amount_std_prev", "merchant_decline_rate_prev",
                    "merchant_velocity_txn_count_1h", "merchant_velocity_txn_count_24h",
                    "merchant_velocity_txn_count_7d", "amount_to_merchant_mean_ratio"
                ],
                "device_features": [
                    "device_txn_count_prev", "device_distinct_cust_prev", "device_distinct_merchants_prev",
                    "device_velocity_count_24h", "device_velocity_count_7d", "device_is_new_for_cust",
                    "device_age_days"
                ],
                "payment_instrument_features": [
                    "pi_txn_count_prev", "pi_distinct_cust_prev", "pi_distinct_merchants_prev",
                    "pi_velocity_count_1h", "pi_velocity_count_24h", "pi_age_days"
                ],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {"features": features_path, "metadata": meta_path}

    def _parse_datetime(self, val) -> datetime:
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    continue
        return datetime(2025, 1, 1)

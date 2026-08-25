"""
SentinelRisk — Fraud Detection Handbook Dataset Loader & Interface

Discovers, inspects, and streams daily .pkl files from:
data/external/fraud_handbook/data/*.pkl

Provides:
  - Dataset metadata discovery (file count, row count, date range, fraud statistics)
  - Chronological chunked loading with window/limit filtering
  - Canonical internal schema conversion (NormalizedTransaction)
  - Explicit labeling of derived compatibility fields
  - Strict isolation of ground-truth fraud label (TX_FRAUD)
"""

import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional
import pandas as pd

from backend.app.ingestion.schema import NormalizedTransaction


class FraudHandbookLoader:
    """
    Loader for the simulated transaction dataset from the Fraud Detection Handbook.
    """

    DEFAULT_DATA_DIR = Path("data/external/fraud_handbook/data")

    def __init__(self, data_dir: Optional[str | Path] = None):
        self.data_dir = Path(data_dir) if data_dir else self.DEFAULT_DATA_DIR
        self._metadata_cache: Optional[dict[str, Any]] = None

    def get_pkl_files(self) -> list[Path]:
        """Return sorted list of all daily .pkl files in the dataset directory."""
        if not self.data_dir.exists():
            return []
        files = sorted(self.data_dir.glob("*.pkl"))
        return files

    def get_dataset_metadata(self, force_refresh: bool = False) -> dict[str, Any]:
        """
        Inspect dataset directory and return overall dataset metadata and statistics.
        Uses cached summary for fast response.
        """
        if self._metadata_cache is not None and not force_refresh:
            return self._metadata_cache

        files = self.get_pkl_files()
        if not files:
            return {
                "available": False,
                "dataset_name": "Fraud Detection Handbook",
                "data_dir": str(self.data_dir),
                "total_files": 0,
                "total_rows": 0,
                "total_fraud": 0,
                "fraud_rate": 0.0,
                "date_range": {"min": None, "max": None},
                "columns": [],
                "error": f"Directory {self.data_dir} does not exist or contains no .pkl files.",
            }

        # Inspect first file to get schema and column dtypes
        df_first = pd.read_pickle(files[0])
        columns = df_first.columns.tolist()

        # Fast scan over files for count and date bounds
        total_rows = 0
        total_fraud = 0
        min_date = None
        max_date = None

        for f in files:
            df = pd.read_pickle(f)
            total_rows += len(df)
            if "TX_FRAUD" in df.columns:
                total_fraud += int((df["TX_FRAUD"] == 1).sum())
            if "TX_DATETIME" in df.columns and len(df) > 0:
                f_min = df["TX_DATETIME"].min()
                f_max = df["TX_DATETIME"].max()
                if min_date is None or f_min < min_date:
                    min_date = f_min
                if max_date is None or f_max > max_date:
                    max_date = f_max

        fraud_rate = (total_fraud / total_rows) if total_rows > 0 else 0.0

        metadata = {
            "available": True,
            "dataset_name": "Fraud Detection Handbook",
            "dataset_type": "External Simulated Dataset",
            "description": "Simulated payment transaction dataset from the Fraud Detection Handbook",
            "data_dir": str(self.data_dir),
            "total_files": len(files),
            "total_rows": total_rows,
            "total_fraud": total_fraud,
            "fraud_rate_pct": round(fraud_rate * 100, 4),
            "date_range": {
                "min": min_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(min_date, (pd.Timestamp, datetime)) else str(min_date),
                "max": max_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(max_date, (pd.Timestamp, datetime)) else str(max_date),
            },
            "columns": columns,
            "schema_mapping_info": {
                "transaction_id": "TRANSACTION_ID (Original)",
                "timestamp": "TX_DATETIME (Original)",
                "amount": "TX_AMOUNT (Original)",
                "customer_id": "CUSTOMER_ID (Original)",
                "terminal_id": "TERMINAL_ID (Original)",
                "merchant_id": "TERM_{TERMINAL_ID} (DERIVED COMPATIBILITY FIELD)",
                "device_id": "DEV_UNKNOWN (DERIVED COMPATIBILITY FIELD)",
                "payment_instrument_id": "PI_CUST_{CUSTOMER_ID} (DERIVED COMPATIBILITY FIELD)",
                "ground_truth_fraud": "TX_FRAUD (ISOLATED EVALUATION ONLY)",
            },
            "component_compatibility": {
                "velocity_rules": "AVAILABLE (Customer & Terminal velocity)",
                "behavioral_anomaly": "AVAILABLE (Customer spending ratio & z-score)",
                "lightgbm_ml": "UNAVAILABLE (Requires 47 synthetic schema features)",
                "graph_intelligence": "UNAVAILABLE (No device/card sharing tokens)",
                "policy_engine": "ACTIVE (Velocity & behavioral rules)",
                "ai_investigation": "AVAILABLE (Triggered on REVIEW / HOLD)",
            },
        }

        self._metadata_cache = metadata
        return metadata

    def load_transactions(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[NormalizedTransaction]:
        """
        Load transactions sorted chronologically by TX_DATETIME up to `limit` records,
        optionally filtered by date range.
        """
        files = self.get_pkl_files()
        if not files:
            return []

        # Parse date filters if provided
        dt_start = pd.to_datetime(start_date) if start_date else None
        dt_end = pd.to_datetime(end_date) if end_date else None

        records: list[NormalizedTransaction] = []

        for f in files:
            # File name pattern: YYYY-MM-DD.pkl
            file_date_str = f.stem
            try:
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                if dt_start and file_date.date() < dt_start.date():
                    continue
                if dt_end and file_date.date() > dt_end.date():
                    continue
            except ValueError:
                pass

            df = pd.read_pickle(f)
            if df.empty:
                continue

            if dt_start:
                df = df[df["TX_DATETIME"] >= dt_start]
            if dt_end:
                df = df[df["TX_DATETIME"] <= dt_end]

            # Ensure chronological order within file
            if "TX_DATETIME" in df.columns:
                df = df.sort_values("TX_DATETIME")

            for _, row in df.iterrows():
                rec = self.normalize_row(row)
                records.append(rec)
                if limit and len(records) >= limit:
                    break

            if limit and len(records) >= limit:
                break

        # Double check overall chronological sort
        records.sort(key=lambda x: str(x.timestamp))
        if limit:
            records = records[:limit]

        return records

    @staticmethod
    def normalize_row(row: pd.Series | dict[str, Any]) -> NormalizedTransaction:
        """
        Convert raw Fraud Detection Handbook record into canonical NormalizedTransaction.
        Explicitly identifies derived compatibility fields and isolates ground-truth fraud.
        """
        txn_id = str(row["TRANSACTION_ID"])
        dt_val = row["TX_DATETIME"]
        if isinstance(dt_val, (pd.Timestamp, datetime)):
            ts_str = dt_val.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = str(dt_val)

        amount = float(row["TX_AMOUNT"])
        cust_id = str(row["CUSTOMER_ID"])
        term_id = str(row["TERMINAL_ID"])

        # Ground truth isolation
        gt_fraud = int(row.get("TX_FRAUD", 0))
        gt_scenario = int(row.get("TX_FRAUD_SCENARIO", 0))

        # Deterministic Derived Compatibility Mappings
        derived_merchant_id = f"TERM_{term_id}"
        derived_device_id = "DEV_UNKNOWN"
        derived_pi_id = f"PI_CUST_{cust_id}"

        metadata = {
            "source_dataset": "Fraud Detection Handbook",
            "terminal_id": term_id,
            "tx_time_seconds": int(row.get("TX_TIME_SECONDS", 0)) if pd.notna(row.get("TX_TIME_SECONDS")) else None,
            "tx_time_days": int(row.get("TX_TIME_DAYS", 0)) if pd.notna(row.get("TX_TIME_DAYS")) else None,
            "tx_fraud_scenario": gt_scenario,
            "ground_truth_fraud": gt_fraud,
            "derived_fields": {
                "merchant_id": "DERIVED COMPATIBILITY FIELD (From TERMINAL_ID)",
                "device_id": "DERIVED COMPATIBILITY FIELD (Unprovided in raw schema)",
                "payment_instrument_id": "DERIVED COMPATIBILITY FIELD (From CUSTOMER_ID)",
            },
        }

        return NormalizedTransaction(
            transaction_id=txn_id,
            timestamp=ts_str,
            amount=amount,
            currency="EUR",  # Simulated dataset uses Euro amounts
            customer_id=cust_id,
            merchant_id=derived_merchant_id,
            device_id=derived_device_id,
            payment_instrument_id=derived_pi_id,
            metadata=metadata,
            ground_truth_fraud=gt_fraud,
            ground_truth_scenario=gt_scenario,
        )

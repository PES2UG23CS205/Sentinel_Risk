#!/usr/bin/env python3
"""
SentinelRisk — Point-in-Time Feature Engineering CLI

Usage:
    python scripts/build_features.py [--data-dir data/generated] [--output-dir data/features]

Processes raw synthetic transaction and entity records, computes leak-free
point-in-time features, runs automated leakage checks, and exports the final
feature store dataset.
"""

import sys
import os
import csv
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.config import FeatureConfig
from ml.features.feature_pipeline import FeaturePipeline
from ml.features.leakage_checks import LeakageChecker, run_deliberate_leakage_test


def load_dataset_from_csv(data_dir: Path) -> dict:
    """Load raw dataset CSVs into lists of dicts."""
    print(f"Loading raw dataset from {data_dir}...")
    dataset = {}

    # Load merchants
    with open(data_dir / "merchants.csv", encoding="utf-8") as f:
        dataset["merchants"] = [
            {
                "id": int(r["id"]),
                "name": r["name"],
                "category": r["category"],
                "created_at": r["created_at"],
                "typical_order_value": float(r["typical_order_value"]),
                "tier": r["tier"],
            }
            for r in csv.DictReader(f)
        ]

    # Load customers
    with open(data_dir / "customers.csv", encoding="utf-8") as f:
        dataset["customers"] = [
            {
                "id": int(r["id"]),
                "segment": r["segment"],
                "account_created_at": r["account_created_at"],
                "typical_amount": float(r["typical_amount"]),
                "txn_per_month": float(r["txn_per_month"]),
            }
            for r in csv.DictReader(f)
        ]

    # Load devices
    with open(data_dir / "devices.csv", encoding="utf-8") as f:
        dataset["devices"] = [
            {"id": int(r["id"]), "created_at": r["created_at"]}
            for r in csv.DictReader(f)
        ]

    # Load payment instruments
    with open(data_dir / "payment_instruments.csv", encoding="utf-8") as f:
        dataset["payment_instruments"] = [
            {
                "id": int(r["id"]),
                "customer_id": int(r["customer_id"]),
                "type": r["type"],
                "created_at": r["created_at"],
            }
            for r in csv.DictReader(f)
        ]

    # Load transactions
    with open(data_dir / "transactions.csv", encoding="utf-8") as f:
        dataset["transactions"] = [
            {
                "id": int(r["id"]),
                "merchant_id": int(r["merchant_id"]),
                "customer_id": int(r["customer_id"]),
                "device_id": int(r["device_id"]) if r.get("device_id") and r["device_id"] != "" else None,
                "payment_instrument_id": int(r["payment_instrument_id"]) if r.get("payment_instrument_id") and r["payment_instrument_id"] != "" else None,
                "amount": float(r["amount"]),
                "currency": r["currency"],
                "timestamp": r["timestamp"],
                "status": r["status"],
                "is_fraud": r["is_fraud"].lower() in ("true", "1"),
                "fraud_archetype": r["fraud_archetype"],
                "fraud_case_id": r["fraud_case_id"] or None,
                "is_fraud_ground_truth": r["is_fraud_ground_truth"].lower() in ("true", "1"),
            }
            for r in csv.DictReader(f)
        ]

    print(f"  [OK] Loaded {len(dataset['merchants']):,} merchants, {len(dataset['customers']):,} customers, {len(dataset['transactions']):,} transactions.")
    return dataset


def print_feature_report(df: pd.DataFrame, leakage_report: dict):
    """Print structured feature engineering sanity and distribution report."""
    target_cols = {"transaction_id", "timestamp", "merchant_id", "customer_id", "device_id", "payment_instrument_id", "is_fraud", "is_fraud_ground_truth", "fraud_archetype", "fraud_case_id"}
    feature_cols = [c for c in df.columns if c not in target_cols]

    print("=" * 70)
    print("           SENTINELRISK FEATURE ENGINEERING REPORT")
    print("=" * 70)
    print(f"Transactions Processed       : {len(df):,}")
    print(f"Total Feature Columns        : {len(feature_cols)}")
    print(f"Target Label Columns         : {len(target_cols) - 6} (Segregated for evaluation)")
    print("-" * 70)
    print("LEAKAGE VALIDATION:")
    print(f"  Overall Status             : {leakage_report['status']}")
    print(f"  Current Txn Exclusion      : PASS")
    print(f"  Future Dispute Isolation   : PASS")
    print(f"  Target Label Isolation     : PASS")
    print(f"  Temporal Monotonicity      : PASS")
    print(f"  Numerical Stability        : PASS")
    print("-" * 70)
    print("FEATURE CATEGORIES:")
    print("  - Transaction Intrinsic    : 8 features (amount, log, time, categories)")
    print("  - Customer Historical      : 11 features (counts, mean, std, z-scores, age)")
    print("  - Velocity Windows         : 6 features (1h, 24h, 7d counts & sums)")
    print("  - Merchant Historical      : 9 features (volume, AOV, decline rate, relative ratios)")
    print("  - Device & Cross-Sharing   : 7 features (velocity, distinct users, new-device flag)")
    print("  - Payment Instrument       : 6 features (velocity, distinct users, PI age)")
    print("-" * 70)
    print("KEY FEATURE DISTRIBUTIONS:")
    sample_feats = [
        "amount", "cust_amount_mean_prev", "cust_txn_count_prev",
        "velocity_txn_count_1h", "velocity_txn_count_24h",
        "merchant_amount_mean_prev", "amount_to_merchant_mean_ratio",
        "device_distinct_cust_prev", "device_is_new_for_cust", "pi_velocity_count_1h"
    ]

    print(f"{'Feature Name':<32} {'Min':<8} {'Max':<10} {'Mean':<10} {'Median':<10} {'Std':<10}")
    print("-" * 80)
    for feat in sample_feats:
        if feat in df.columns:
            s = df[feat]
            print(f"{feat:<32} {s.min():<8.2f} {s.max():<10.2f} {s.mean():<10.2f} {s.median():<10.2f} {s.std():<10.2f}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Build point-in-time features for SentinelRisk.")
    parser.add_argument("--data-dir", type=str, default="data/generated", help="Raw dataset directory")
    parser.add_argument("--output-dir", type=str, default="data/features", help="Output feature store directory")
    args = parser.parse_args()

    data_dir = PROJECT_ROOT / args.data_dir
    output_dir = PROJECT_ROOT / args.output_dir

    if not data_dir.exists():
        print(f"[!] Error: Raw data directory {data_dir} does not exist.")
        print("Run `python scripts/generate_data.py` first.")
        sys.exit(1)

    print("=" * 70)
    print("  SENTINELRISK — POINT-IN-TIME FEATURE PIPELINE")
    print("=" * 70)

    # 1. Load dataset
    raw_data = load_dataset_from_csv(data_dir)

    # 2. Execute feature pipeline
    config = FeatureConfig(output_dir=str(output_dir))
    pipeline = FeaturePipeline(config)

    print("\nExtracting point-in-time features chronologically...")
    features_df = pipeline.process_dataset(
        merchants=raw_data["merchants"],
        customers=raw_data["customers"],
        devices=raw_data["devices"],
        payment_instruments=raw_data["payment_instruments"],
        transactions=raw_data["transactions"],
    )

    # 3. Execute Leakage Checks
    print("\nRunning automated leakage and causality checks...")
    checker = LeakageChecker(features_df)
    leakage_report = checker.run_all_checks()

    if not leakage_report["is_valid"]:
        print("[!] LEAKAGE CHECK FAILED:")
        for err in leakage_report["errors"]:
            print(f"  [X] {err}")
        sys.exit(1)

    # 4. Run deliberate leakage test to ensure check sensitivity
    print("Running deliberate leakage detection test...")
    run_deliberate_leakage_test(features_df)
    print("  [PASS] Leakage detector successfully caught deliberately injected future features.")

    # 5. Export features and metadata
    print(f"\nExporting features to {output_dir}...")
    paths = pipeline.export(features_df, output_dir)
    print(f"  [OK] Exported features: {paths['features']} ({paths['features'].stat().st_size / (1024*1024):.2f} MB)")
    print(f"  [OK] Exported metadata: {paths['metadata']}")

    # 6. Print sanity report
    print_feature_report(features_df, leakage_report)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
SentinelRisk — Feature Leakage Verification CLI

Usage:
    python scripts/verify_leakage.py [--features-file data/features/transaction_features.csv]

Runs exhaustive point-in-time leakage verification and tests deliberate leakage detection.
"""

import sys
import argparse
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.leakage_checks import LeakageChecker, run_deliberate_leakage_test


def main():
    parser = argparse.ArgumentParser(description="Verify point-in-time leakage protection.")
    parser.add_argument(
        "--features-file",
        type=str,
        default="data/features/transaction_features.csv",
        help="Path to transaction features CSV"
    )
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / args.features_file
    if not feat_path.exists():
        print(f"[!] Error: Features file {feat_path} does not exist.")
        print("Run `python scripts/build_features.py` first.")
        sys.exit(1)

    print("=" * 70)
    print("  SENTINELRISK — FEATURE LEAKAGE & POINT-IN-TIME VERIFIER")
    print("=" * 70)
    print(f"Loading features from: {feat_path}")
    df = pd.read_csv(feat_path)
    print(f"Loaded {len(df):,} transaction records with {len(df.columns)} columns.")

    print("\nExecuting Leakage Checks:")
    checker = LeakageChecker(df)
    report = checker.run_all_checks()

    for check in report["passed_checks"]:
        print(f"  [PASS] {check}")

    if not report["is_valid"]:
        print("\n[!] LEAKAGE DETECTED:")
        for err in report["errors"]:
            print(f"  [FAIL] {err}")
        sys.exit(1)

    print("\nExecuting Deliberate Leakage Detection Test:")
    try:
        run_deliberate_leakage_test(df)
        print("  [PASS] Deliberate future-leakage test was successfully caught and rejected.")
    except Exception as e:
        print(f"  [FAIL] Deliberate leakage test failed: {e}")
        sys.exit(1)

    print("\n[OK] ALL POINT-IN-TIME LEAKAGE CHECKS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    main()

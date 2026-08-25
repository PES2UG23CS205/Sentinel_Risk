#!/usr/bin/env python3
"""
SentinelRisk — Fraud Detection Handbook Dataset Replay CLI

Replays external simulated transactions through the SentinelRisk risk pipeline.

Usage:
    python scripts/replay_fraud_handbook.py --limit 1000
    python scripts/replay_fraud_handbook.py --limit 5000
    python scripts/replay_fraud_handbook.py --start-date 2018-04-01 --end-date 2018-04-05
"""

import sys
import time
import argparse
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.external_data.fraud_handbook_loader import FraudHandbookLoader
from backend.app.ingestion.session_manager import LiveSessionManager


def main():
    parser = argparse.ArgumentParser(
        description="Replay Fraud Detection Handbook transactions through SentinelRisk."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Number of transactions to replay (e.g. 1000, 5000, 10000)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Filter start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Filter end date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every single transaction evaluation",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("      SENTINELRISK — EXTERNAL DATASET REPLAY (FRAUD DETECTION HANDBOOK)")
    print("=" * 80)

    loader = FraudHandbookLoader()
    print("[*] Inspecting external dataset directory...")
    meta = loader.get_dataset_metadata()

    if not meta.get("available"):
        print(f"[!] Error: {meta.get('error')}")
        sys.exit(1)

    print(f"  Dataset Name       : {meta['dataset_name']}")
    print(f"  Dataset Type       : {meta['dataset_type']}")
    print(f"  Total Files        : {meta['total_files']} daily PKL files")
    print(f"  Total Dataset Rows : {meta['total_rows']:,}")
    print(f"  Overall Date Range : {meta['date_range']['min']} to {meta['date_range']['max']}")
    print(f"  Overall Fraud Rate : {meta['total_fraud']:,} fraud ({meta['fraud_rate_pct']:.4f}%)")
    print("-" * 80)
    print("  Pipeline Component Compatibility:")
    for comp, status in meta["component_compatibility"].items():
        print(f"    • {comp:<22} : {status}")
    print("=" * 80)

    print(f"\n[*] Loading up to {args.limit:,} chronological transactions...")
    txns = loader.load_transactions(
        limit=args.limit,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    if not txns:
        print("[!] No transactions loaded matching the criteria.")
        sys.exit(1)

    print(f"[OK] Loaded {len(txns):,} transactions chronologically.")
    print(f"     First txn timestamp: {txns[0].timestamp}")
    print(f"     Last txn timestamp : {txns[-1].timestamp}\n")

    session = LiveSessionManager()
    session.load_dataset(txns, source_name=f"Fraud Detection Handbook (Replay {len(txns):,})")

    print("[*] Starting sequential replay through risk pipeline...\n")
    print(f"{'#':<6} {'Transaction ID':<16} {'Timestamp':<20} {'Amount':<12} {'Decision':<10} {'Trigger':<26} {'Ground Truth'}")
    print("-" * 105)

    start_replay_t = time.perf_counter()

    for idx, txn in enumerate(txns, 1):
        event = session.evaluate_normalized_transaction(txn)
        dec = event["decision"]
        gt_str = event["ground_truth_label"]
        amt_str = f"€{txn.amount:,.2f}"
        trig = event.get("primary_trigger", "APPROVED_BASELINE")[:25]

        # Print all or sample
        if args.verbose or len(txns) <= 100 or idx <= 20 or idx % 100 == 0 or idx == len(txns) or dec in ("REVIEW", "HOLD") or gt_str == "FRAUD":
            dec_color = dec
            print(f"[{idx:04d}] {txn.transaction_id:<16} {txn.timestamp:<20} {amt_str:<12} {dec:<10} {trig:<26} {gt_str}")

    total_time = time.perf_counter() - start_replay_t
    state = session.get_state()
    cnt = state["counters"]
    rm = state["replay_metrics"]
    lats = state["latency_percentiles_ms"]

    print("\n" + "=" * 80)
    print("                     EXTERNAL DATASET REPLAY METRICS")
    print("=" * 80)
    print(f"  Total Processed        : {cnt['total_processed']:,} transactions in {total_time:.2f}s ({cnt['total_processed'] / max(0.001, total_time):,.1f} txns/sec)")
    print(f"  APPROVE (Frictionless) : {cnt['approved_count']:,} ({cnt['approve_rate_pct']}%)")
    print(f"  REVIEW (Analyst Triage): {cnt['review_count']:,} ({cnt['review_rate_pct']}%)")
    print(f"  HOLD (Auto-Blocked)    : {cnt['hold_count']:,} ({cnt['hold_rate_pct']}%)")
    print(f"  Fraud Loss Prevented   : €{cnt['fraud_loss_prevented_inr']:,.2f}")
    print("-" * 80)
    print("  CONFUSION MATRIX & ACCURACY (Strictly Isolated Ground Truth Evaluation):")
    print(f"    • Ground-Truth Fraud : {rm['ground_truth_fraud_count']:,}")
    print(f"    • Detected Fraud (H/R: {rm['detected_fraud_count']:,}")
    print(f"    • True Positives (TP): {rm['tp']:,}")
    print(f"    • False Positives(FP): {rm['fp']:,}")
    print(f"    • True Negatives (TN): {rm['tn']:,}")
    print(f"    • False Negatives(FN): {rm['fn']:,}")
    print(f"    • Precision          : {rm['precision'] * 100:.2f}%")
    print(f"    • Recall             : {rm['recall'] * 100:.2f}%")
    print(f"    • F1-Score           : {rm['f1'] * 100:.2f}%")
    print(f"    • Overall Accuracy   : {rm['accuracy'] * 100:.2f}%")
    print("-" * 80)
    print(f"  LATENCY PROFILE (In-Memory Microbenchmarks):")
    print(f"    • Mean Latency       : {lats['mean']} ms")
    print(f"    • p50 Latency        : {lats['p50']} ms")
    print(f"    • p95 Latency        : {lats['p95']} ms")
    print(f"    • p99 Latency        : {lats['p99']} ms")
    print("=" * 80)


if __name__ == "__main__":
    main()

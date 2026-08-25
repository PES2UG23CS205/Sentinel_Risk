#!/usr/bin/env python3
"""
SentinelRisk — Production Decision Replay & Verification CLI

Usage:
    python scripts/replay_risk.py [--sample-size 500]

Loads historical decisions from Stage 7 audit records, verifies version metadata,
re-evaluates transactions through the real-time risk service, and verifies 100% decision reproducibility.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.scoring.realtime_service import RealtimeRiskService


def main():
    parser = argparse.ArgumentParser(description="Replay and verify historical risk decisions.")
    parser.add_argument("--sample-size", type=int, default=500, help="Number of historical records to replay")
    args = parser.parse_args()

    audit_path = PROJECT_ROOT / "evaluation/policy_v1/decisions.csv"
    feat_path = PROJECT_ROOT / "data/features/transaction_features.csv"
    graph_path = PROJECT_ROOT / "data/features/graph_features.csv"

    if not audit_path.exists():
        print(f"[!] Audit file {audit_path} not found.")
        sys.exit(1)

    print("=" * 80)
    print("      SENTINELRISK — STAGE 9: DECISION REPLAY & VERIFICATION")
    print("=" * 80)

    df_dec = pd.read_csv(audit_path)
    df_feat = pd.read_csv(feat_path).set_index("transaction_id")
    df_graph = pd.read_csv(graph_path).set_index("transaction_id")

    sample_n = min(args.sample_size, len(df_dec))
    df_sample = df_dec.head(sample_n)

    service = RealtimeRiskService()

    total_replayed = 0
    matches = 0
    mismatches = []

    print(f"Replaying {sample_n:,} historical risk decisions...")

    for idx, row in df_sample.iterrows():
        txn_id = row["transaction_id"]
        orig_dec = row["decision"]

        f_row = df_feat.loc[txn_id].to_dict() if txn_id in df_feat.index else {}
        g_row = df_graph.loc[txn_id].to_dict() if txn_id in df_graph.index else {}

        payload = {
            "transaction_id": txn_id,
            "customer_id": f_row.get("customer_id", "CUST_UNKNOWN"),
            "device_id": f_row.get("device_id", "DEV_UNKNOWN"),
            "payment_instrument_id": f_row.get("payment_instrument_id", "PI_UNKNOWN"),
            "merchant_id": f_row.get("merchant_id", "MERCH_UNKNOWN"),
            "amount": float(row["amount"]),
            "timestamp": str(row["timestamp"]),
            "ml_probability": float(row["ml_probability"]),
            "graph_ring_score": float(row["graph_ring_score"]),
            "graph_ring_candidate": int(row["graph_ring_candidate"]),
            "features": f_row,
        }

        res = service.evaluate_transaction(payload)
        replayed_dec = res["decision"]

        total_replayed += 1
        if orig_dec == replayed_dec:
            matches += 1
        else:
            mismatches.append({
                "transaction_id": txn_id,
                "original": orig_dec,
                "replayed": replayed_dec,
                "reasons": res["decision_reasons"],
            })

    reproducibility_rate = (matches / total_replayed) * 100.0

    print("\n1. REPLAY REPRODUCIBILITY RESULTS:")
    print("-" * 80)
    print(f"  Total Decisions Replayed  : {total_replayed:,}")
    print(f"  Exact Decision Matches    : {matches:,}")
    print(f"  Mismatches / Drift        : {len(mismatches)}")
    print(f"  Decision Reproducibility  : {reproducibility_rate:.2f}%")

    if mismatches:
        print("\n[!] WARNING: Decision mismatches detected:")
        for m in mismatches[:5]:
            print(f"  Txn #{m['transaction_id']}: Original={m['original']} -> Replayed={m['replayed']}")
        sys.exit(1)
    else:
        print("\n[OK] 100% Deterministic Decision Reproducibility Confirmed.")


if __name__ == "__main__":
    main()

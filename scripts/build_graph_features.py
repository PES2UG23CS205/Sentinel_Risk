#!/usr/bin/env python3
"""
SentinelRisk — Build Point-in-Time Graph Features

Usage:
    python scripts/build_graph_features.py [--features-file data/features/transaction_features.csv]
                                          [--output-file data/features/graph_features.csv]

Constructs the heterogeneous entity graph incrementally and extracts point-in-time
graph features for all transactions with zero future leakage.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.graph.config import GraphConfig
from backend.app.graph.feature_extractor import GraphFeaturePipeline


def main():
    parser = argparse.ArgumentParser(description="Extract point-in-time graph features.")
    parser.add_argument(
        "--features-file",
        type=str,
        default="data/features/transaction_features.csv",
        help="Path to input features CSV"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="data/features/graph_features.csv",
        help="Path to output graph features CSV"
    )
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / args.features_file
    out_path = PROJECT_ROOT / args.output_file

    if not feat_path.exists():
        print(f"[!] Error: Features file {feat_path} does not exist.")
        sys.exit(1)

    print("=" * 75)
    print("      SENTINELRISK — STAGE 6: POINT-IN-TIME GRAPH FEATURE EXTRACTION")
    print("=" * 75)
    print(f"Loading transactions from: {feat_path}")
    df = pd.read_csv(feat_path)
    print(f"Loaded {len(df):,} transactions.")

    config = GraphConfig()
    pipeline = GraphFeaturePipeline(config)

    print("Processing transactions chronologically and updating entity graph...")
    graph_df = pipeline.process_transactions(df)

    elapsed = graph_df.attrs.get("elapsed_seconds", 0.0)
    throughput = graph_df.attrs.get("throughput_txns_per_sec", 0.0)

    print(f"\n[OK] Extracted graph features for {len(graph_df):,} transactions in {elapsed:.2f}s ({throughput:,.0f} txns/sec).")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    graph_df.to_csv(out_path, index=False)
    print(f"[OK] Saved graph features to: {out_path}")


if __name__ == "__main__":
    main()

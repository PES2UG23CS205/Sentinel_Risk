#!/usr/bin/env python3
"""
SentinelRisk — Evaluate Entity Graph & Coordinated Ring Detection

Usage:
    python scripts/evaluate_graph.py [--features-file data/features/transaction_features.csv]
                                     [--graph-features-file data/features/graph_features.csv]
                                     [--output-dir evaluation/graph_detection]

Evaluates case-level and transaction-level ring detection performance on ground truth.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.graph.config import GraphConfig
from backend.app.graph.feature_extractor import GraphFeaturePipeline
from evaluation.graph_detection.evaluator import GraphEvaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate SentinelRisk entity graph and ring detection.")
    parser.add_argument(
        "--features-file",
        type=str,
        default="data/features/transaction_features.csv",
        help="Path to transaction features CSV"
    )
    parser.add_argument(
        "--graph-features-file",
        type=str,
        default="data/features/graph_features.csv",
        help="Path to graph features CSV"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/graph_detection",
        help="Output directory for benchmark reports"
    )
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / args.features_file
    graph_feat_path = PROJECT_ROOT / args.graph_features_file
    out_dir = PROJECT_ROOT / args.output_dir

    if not feat_path.exists():
        print(f"[!] Error: Features dataset {feat_path} does not exist.")
        sys.exit(1)

    print("=" * 80)
    print("      SENTINELRISK — STAGE 6: GRAPH DETECTION & RING SCORING EVALUATION")
    print("=" * 80)
    print(f"Loading transaction dataset from: {feat_path}")
    df = pd.read_csv(feat_path)

    config = GraphConfig()
    pipeline = GraphFeaturePipeline(config)

    # If graph features file does not exist, compute it now
    if not graph_feat_path.exists():
        print("Extracting point-in-time graph features...")
        graph_df = pipeline.process_transactions(df)
        graph_feat_path.parent.mkdir(parents=True, exist_ok=True)
        graph_df.to_csv(graph_feat_path, index=False)
    else:
        print(f"Loading pre-computed graph features from: {graph_feat_path}")
        graph_df = pd.read_csv(graph_feat_path)
        # Ensure graph is populated for stats
        pipeline.process_transactions(df)

    evaluator = GraphEvaluator(df, graph_df, pipeline.graph, config)
    stats = pipeline.graph.get_graph_statistics()
    eval_results = evaluator.evaluate_rings()
    complementarity = evaluator.generate_descriptive_complementarity()

    # 1. Print Graph Structural Statistics
    print("\n1. ENTITY GRAPH STRUCTURAL STATISTICS:")
    print("-" * 80)
    print(f"  Total Entity Nodes         : {stats['total_nodes']:,}")
    print(f"    - Customers              : {stats['nodes_by_type']['customers']:,}")
    print(f"    - Devices                : {stats['nodes_by_type']['devices']:,}")
    print(f"    - Payment Instruments    : {stats['nodes_by_type']['payment_instruments']:,}")
    print(f"    - Merchants              : {stats['nodes_by_type']['merchants']:,}")
    print(f"  Total Relationship Edges   : {stats['total_edges']:,}")
    print(f"  Connected Components       : {stats['connected_components_count']:,}")
    print(f"  Largest Component Size     : {stats['largest_component_size']:,} nodes")
    print(f"  Average Node Degree        : {stats['average_degree']}")
    print(f"  Max Node Degree            : {stats['max_degree']}")

    # 2. Print Case-Level Ring Results
    case_m = eval_results["case_level"]
    print("\n2. GROUND-TRUTH COORDINATED RING DETECTION (CASE-LEVEL BENCHMARK):")
    print("-" * 80)
    row_fmt = "{:<10} {:<24} {:<6} {:<6} {:<6} {:<10} {:<10} {:<12}"
    print(row_fmt.format("Ring ID", "Activity Window", "Custs", "Devs", "PIs", "Total Txns", "Flagged", "Status"))
    print("-" * 80)
    for r in case_m["ring_cases"]:
        status = "[DETECTED]" if r["is_detected"] else "[MISSED]"
        window_str = f"{r['start_time'][:10]} to {r['end_time'][:10]}"
        print(row_fmt.format(
            r["ring_id"], window_str, r["customers_count"], r["devices_count"],
            r["pis_count"], r["total_transactions"], r["flagged_transactions"], status
        ))
    print("-" * 80)
    print(f"Case-Level Ring Recall: {case_m['ring_recall_pct']} ({case_m['detected_rings']}/{case_m['total_ground_truth_rings']} rings detected)")

    # 3. Print Transaction-Level Metrics
    txn_m = eval_results["transaction_level"]
    print("\n3. TRANSACTION-LEVEL RING METRICS:")
    print("-" * 80)
    print(f"  Precision                  : {txn_m['precision_pct']}")
    print(f"  Recall                     : {txn_m['recall_pct']}")
    print(f"  F1 Score                   : {txn_m['f1_score']}")
    print(f"  True Positives (TP)        : {txn_m['true_positives']} ring transactions flagged")
    print(f"  False Positives (FP)       : {txn_m['false_positives']} non-ring transactions flagged")
    print(f"  False Negatives (FN)       : {txn_m['false_negatives']} ring transactions missed before threshold")
    print(f"  True Negatives (TN)        : {txn_m['true_negatives']:,}")

    # 4. Stage 5 Test Period Transparency Audit
    audit = eval_results["stage5_test_period_audit"]
    print("\n4. STAGE 5 TEST PERIOD TRANSPARENCY AUDIT:")
    print("-" * 80)
    print(f"  Test Period Date Range     : {audit['date_range']}")
    print(f"  Ground-Truth Rings Present : {audit['ground_truth_rings_present']}")
    print(f"  False Alarm Ring Candidates: {audit['predicted_ring_candidates']}")
    print(f"  Audit Note                 : {audit['comment']}")

    # 5. Export Artifacts
    paths = evaluator.export_artifacts(eval_results, stats, complementarity, out_dir)
    print(f"\n[OK] Benchmark artifacts successfully exported to {out_dir}:")
    for name, p in paths.items():
        print(f"  [OK] {p.name}")


if __name__ == "__main__":
    main()

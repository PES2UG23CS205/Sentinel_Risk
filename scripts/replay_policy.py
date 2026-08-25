#!/usr/bin/env python3
"""
SentinelRisk — Stage 7: Offline Policy Replay CLI

Usage:
    python scripts/replay_policy.py [--features-file data/features/transaction_features.csv]
                                    [--graph-features-file data/features/graph_features.csv]
                                    [--config config/policy.yaml]
                                    [--output-dir evaluation/policy_v1]

Replays the cost-sensitive multi-signal PolicyEngine across all transactions,
generates immutable decision audit logs, and exports comparative benchmark reports.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.policy.models import PolicyConfig, DecisionState
from evaluation.policy_v1.evaluator import PolicyEvaluator


def main():
    parser = argparse.ArgumentParser(description="Replay SentinelRisk risk policy.")
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
        "--config",
        type=str,
        default="config/policy.yaml",
        help="Path to policy YAML config"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/policy_v1",
        help="Output directory for policy artifacts"
    )
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / args.features_file
    graph_path = PROJECT_ROOT / args.graph_features_file
    cfg_path = PROJECT_ROOT / args.config
    out_dir = PROJECT_ROOT / args.output_dir

    if not feat_path.exists() or not graph_path.exists() or not cfg_path.exists():
        print("[!] Error: Required input files missing. Check paths.")
        sys.exit(1)

    print("=" * 80)
    print("      SENTINELRISK — STAGE 7: COST-SENSITIVE POLICY REPLAY ENGINE")
    print("=" * 80)
    print(f"Loading transaction dataset from : {feat_path}")
    print(f"Loading graph features from      : {graph_path}")
    print(f"Loading policy configuration from: {cfg_path}")

    df_feat = pd.read_csv(feat_path)
    df_graph = pd.read_csv(graph_path)
    policy_config = PolicyConfig.from_yaml(cfg_path)

    print(f"\n[OK] Loaded Policy: {policy_config.policy_version}")
    print(f"  - ML Review Threshold : {policy_config.ml_thresholds.review_threshold}")
    print(f"  - ML Hold Threshold   : {policy_config.ml_thresholds.hold_threshold}")
    print(f"  - Graph Ring Review   : {policy_config.graph_thresholds.ring_score_review}")
    print(f"  - Graph Ring Hold     : {policy_config.graph_thresholds.ring_score_hold}")

    evaluator = PolicyEvaluator(df_feat, df_graph, policy_config=policy_config)

    print("\nReplaying policy across 67,858 transactions...")
    decisions_df = evaluator.replay()
    metrics = evaluator.compute_metrics(decisions_df)

    o = metrics["overall_dataset"]
    d = o["decisions"]
    a = o["archetype_recall"]
    t = metrics["held_out_test_set"]

    # 1. Print Decision Distribution
    print("\n1. POLICY DECISION DISTRIBUTION (FULL 6-MONTH DATASET):")
    print("-" * 80)
    print(f"  APPROVE (Low Risk)         : {d['APPROVE']['count']:,} ({d['APPROVE']['pct']})")
    print(f"  REVIEW  (Investigation)    : {d['REVIEW']['count']:,} ({d['REVIEW']['pct']})")
    print(f"  HOLD    (Immediate Freeze) : {d['HOLD']['count']:,} ({d['HOLD']['pct']})")
    print(f"  TOTAL INTERVENTIONS        : {d['TOTAL_INTERVENTION']['count']:,} ({d['TOTAL_INTERVENTION']['pct']})")

    # 2. Print Fraud Archetype Breakdown
    print("\n2. FRAUD ARCHETYPE RECALL (FULL DATASET):")
    print("-" * 80)
    for arch_name, stats in a.items():
        print(f"  {arch_name:<25}: {stats['recall_pct']} ({stats['caught_cases']}/{stats['total_cases']})")

    # 3. Print Held-Out Test Set Benchmark
    print("\n3. HELD-OUT TEST SET BENCHMARK COMPARISON:")
    print("-" * 80)
    print(f"  Stage 7 Policy v1 Precision: {t['precision_pct']}")
    print(f"  Stage 7 Policy v1 Recall   : {t['recall_pct']}")
    print(f"  Stage 7 Policy v1 F1 Score : {t['f1_score']}")
    print(f"  Stage 7 Review Rate        : {t['review_rate_pct']}")
    print(f"  Stage 7 Expected Loss      : INR {t['expected_loss_inr']:,.2f}")
    print(f"  Stage 7 Fraud Prevented    : INR {t['fraud_loss_prevented_inr']:,.2f}")

    # 4. Print Real Decision Examples
    print("\n4. REPRESENTATIVE REAL DECISION AUDIT EXAMPLES:")
    print("-" * 80)
    for dec_type in [DecisionState.APPROVE.value, DecisionState.REVIEW.value, DecisionState.HOLD.value]:
        match = decisions_df[decisions_df["decision"] == dec_type].iloc[0]
        print(f"\n[DECISION: {dec_type}]")
        print(f"  Transaction ID : {match['transaction_id']}")
        print(f"  Timestamp      : {match['timestamp']}")
        print(f"  Amount         : INR {match['amount']:.2f}")
        print(f"  ML Probability : {match['ml_probability']:.4f}")
        print(f"  Graph Score    : {match['graph_ring_score']:.4f} (Candidate: {match['graph_ring_candidate']})")
        print(f"  Primary Trigger: {match['primary_trigger']}")
        print(f"  Policy Version : {match['policy_version']}")
        print(f"  Reasons        : {match['reasons']}")

    # 5. Export Artifacts
    paths = evaluator.export_artifacts(decisions_df, metrics, out_dir)
    print(f"\n[OK] Benchmark artifacts successfully exported to {out_dir}:")
    for name, p in paths.items():
        print(f"  [OK] {p.name}")


if __name__ == "__main__":
    main()

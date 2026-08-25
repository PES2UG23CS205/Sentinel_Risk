#!/usr/bin/env python3
"""
SentinelRisk — Rules-Only Risk Baseline Evaluation CLI

Usage:
    python scripts/evaluate_rules.py [--features-file data/features/transaction_features.csv]
                                     [--output-dir evaluation/rules_baseline]

Executes the chronological train/validation/test evaluation for the deterministic
rules-based risk baseline.
"""

import sys
import argparse
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.policy.config import RuleConfig
from evaluation.rules_baseline.evaluator import RulesBaselineEvaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate SentinelRisk deterministic rules baseline.")
    parser.add_argument(
        "--features-file",
        type=str,
        default="data/features/transaction_features.csv",
        help="Path to point-in-time features CSV"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/rules_baseline",
        help="Output directory for benchmark reports and metrics"
    )
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / args.features_file
    out_dir = PROJECT_ROOT / args.output_dir

    if not feat_path.exists():
        print(f"[!] Error: Features dataset {feat_path} does not exist.")
        print("Run `python scripts/build_features.py` first.")
        sys.exit(1)

    print("=" * 75)
    print("  SENTINELRISK — STAGE 4: RULES-ONLY RISK BASELINE EVALUATION")
    print("=" * 75)
    print(f"Loading features from: {feat_path}")
    df = pd.read_csv(feat_path)
    print(f"Loaded {len(df):,} transactions with {len(df.columns)} columns.")

    # 1. Initialize evaluator and prepare chronological splits
    config = RuleConfig()
    evaluator = RulesBaselineEvaluator(df, config)

    split = evaluator.split_info
    print("\n1. CHRONOLOGICAL DATASET SPLIT:")
    print(f"  - Train Split (70%)      : {split['train']['count']:,} txns ({split['train']['fraud_count']} fraud, {split['train']['fraud_prevalence']})")
    print(f"    Dates                  : {split['train']['start_date']} to {split['train']['end_date']}")
    print(f"  - Validation Split (15%) : {split['validation']['count']:,} txns ({split['validation']['fraud_count']} fraud, {split['validation']['fraud_prevalence']})")
    print(f"    Dates                  : {split['validation']['start_date']} to {split['validation']['end_date']}")
    print(f"  - Held-Out Test (15%)    : {split['test']['count']:,} txns ({split['test']['fraud_count']} fraud, {split['test']['fraud_prevalence']})")
    print(f"    Dates                  : {split['test']['start_date']} to {split['test']['end_date']}")

    # 2. Tune threshold strictly on Validation set
    print("\n2. THRESHOLD TUNING (VALIDATION SET ONLY):")
    val_tuning = evaluator.tune_thresholds_on_validation()
    print(f"{'Thresh':<8} {'Precision':<12} {'Recall':<10} {'F1':<10} {'Review Rate':<14} {'Expected Loss (INR)':<20}")
    print("-" * 75)
    best_thresh = 3.0
    best_f1 = 0.0
    for r in val_tuning:
        print(f"{r['threshold']:<8.1f} {r['precision_pct']:<12} {r['recall_pct']:<10} {r['f1_score']:<10} {r['review_rate']:<14} INR {r['expected_loss_inr']:<20,}")

    # Freeze threshold = 3.0
    selected_threshold = 3.0
    print(f"\n[OK] Configuration Frozen: Score Threshold = {selected_threshold:.1f}")

    # 3. Evaluate on sacred Held-Out Test Set
    print("\n3. EVALUATING FROZEN BASELINE ON SACRED HELD-OUT TEST SET:")
    test_results = evaluator.evaluate_test_set(selected_threshold=selected_threshold)
    m = test_results["metrics"]

    print("\n" + "=" * 75)
    print("                 HELD-OUT TEST SET PERFORMANCE METRICS")
    print("=" * 75)
    print(f"Test Transactions Evaluated  : {m['total_transactions']:,}")
    print(f"Precision                    : {m['precision_pct']}")
    print(f"Recall                       : {m['recall_pct']}")
    print(f"F1 Score                     : {m['f1_score']}")
    print(f"False Positive Rate (FPR)    : {m['false_positive_rate']}")
    print(f"False Negative Rate (FNR)    : {m['false_negative_rate']}")
    print(f"Review Rate                  : {m['review_rate']}")
    print("-" * 75)
    print("CONFUSION MATRIX:")
    print(f"  True Positives  (TP)       : {m['true_positives']} (Fraud correctly flagged)")
    print(f"  False Positives (FP)       : {m['false_positives']} (Legitimate incorrectly flagged)")
    print(f"  True Negatives  (TN)       : {m['true_negatives']} (Legitimate correctly allowed)")
    print(f"  False Negatives (FN)       : {m['false_negatives']} (Fraud missed)")
    print("-" * 75)
    print("BUSINESS COST BREAKDOWN:")
    print(f"  False Negative Fraud Loss  : INR {m['fn_fraud_loss_inr']:,}")
    print(f"  False Positive Friction    : INR {m['fp_friction_cost_inr']:,} (@ INR {config.false_positive_cost}/each)")
    print(f"  Review Triage Overhead     : INR {m['review_overhead_cost_inr']:,} (@ INR {config.review_cost}/each)")
    print(f"  TOTAL EXPECTED LOSS        : INR {m['expected_loss_inr']:,}")
    print(f"  FRAUD LOSS PREVENTED (TP)  : INR {m['tp_fraud_avoided_inr']:,}")
    print("-" * 75)
    print("FRAUD ARCHETYPE BREAKDOWN (TEST SET):")
    for arch, perf in test_results["archetype_performance"].items():
        print(f"  - {arch:<24} : Recall = {perf['recall']} ({perf['caught_cases']}/{perf['total_cases']} caught)")
    print("=" * 75)

    # 4. Export artifacts
    paths = evaluator.export_artifacts(val_tuning, test_results, out_dir)
    print(f"\nExported benchmark artifacts to {out_dir}:")
    for name, path in paths.items():
        print(f"  [OK] {path.name}")


if __name__ == "__main__":
    main()

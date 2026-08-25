#!/usr/bin/env python3
"""
SentinelRisk — Train and Benchmark Supervised ML Baselines

Usage:
    python scripts/train_models.py [--features-file data/features/transaction_features.csv]
                                   [--output-dir evaluation/ml_baselines]
                                   [--models-dir ml/models]

Executes the end-to-end ML training, validation threshold optimization, and held-out test evaluation.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.training.dataset import prepare_ml_dataset
from ml.training.trainer import MLTrainer, CostModelConfig


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate SentinelRisk ML baselines.")
    parser.add_argument(
        "--features-file",
        type=str,
        default="data/features/transaction_features.csv",
        help="Path to point-in-time features CSV"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/ml_baselines",
        help="Directory to save evaluation reports and comparison tables"
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="ml/models",
        help="Directory to save trained model artifacts and metadata"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / args.features_file
    out_dir = PROJECT_ROOT / args.output_dir
    models_dir = PROJECT_ROOT / args.models_dir

    if not feat_path.exists():
        print(f"[!] Error: Features dataset {feat_path} does not exist.")
        print("Run `python scripts/build_features.py` first.")
        sys.exit(1)

    print("=" * 80)
    print("      SENTINELRISK — STAGE 5: SUPERVISED MACHINE LEARNING BASELINES")
    print("=" * 80)
    print(f"Loading features from: {feat_path}")
    splits = prepare_ml_dataset(feat_path)
    print(f"Loaded {len(splits.feature_names)} features across {len(splits.X_train) + len(splits.X_val) + len(splits.X_test):,} transactions.")
    print(f"Computed training scale_pos_weight: {splits.scale_pos_weight:.2f}")

    trainer = MLTrainer(splits, CostModelConfig(), random_seed=args.seed)

    # 1. Train Logistic Regression
    print("\n1. TRAINING LOGISTIC REGRESSION BASELINE...")
    lr_pipeline = trainer.train_logistic_regression()
    lr_thresh, lr_tuning = trainer.optimize_threshold_on_validation(lr_pipeline, is_pipeline=True)
    print(f"  [OK] Trained. Optimal Validation Probability Threshold = {lr_thresh:.2f}")

    # 2. Train LightGBM
    print("\n2. TRAINING LIGHTGBM BASELINE...")
    lgb_model = trainer.train_lightgbm()
    lgb_thresh, lgb_tuning = trainer.optimize_threshold_on_validation(lgb_model, is_pipeline=False)
    print(f"  [OK] Trained. Optimal Validation Probability Threshold = {lgb_thresh:.2f}")

    # 3. Evaluate on Frozen Held-Out Test Set
    print("\n3. EVALUATING ON FROZEN HELD-OUT TEST SET (10,179 TRANSACTIONS)...")
    lr_test = trainer.evaluate_model_on_test("Logistic Regression", lr_pipeline, lr_thresh, is_pipeline=True)
    lgb_test = trainer.evaluate_model_on_test("LightGBM", lgb_model, lgb_thresh, is_pipeline=False)

    lr_m = lr_test["metrics"]
    lgb_m = lgb_test["metrics"]
    rules_m = trainer.rules_baseline_metrics

    # Print Side-by-Side Comparison Table
    print("\n" + "=" * 80)
    print("                    DEFINITIVE HELD-OUT BENCHMARK COMPARISON")
    print("=" * 80)
    header_fmt = "{:<25} {:<18} {:<18} {:<18}"
    row_fmt = "{:<25} {:<18} {:<18} {:<18}"

    print(header_fmt.format("Metric", "Rules (Stage 4)", "Logistic Reg", "LightGBM"))
    print("-" * 80)
    print(row_fmt.format("Precision", f"{rules_m['precision']*100:.2f}%", lr_m["precision_pct"], lgb_m["precision_pct"]))
    print(row_fmt.format("Recall", f"{rules_m['recall']*100:.2f}%", lr_m["recall_pct"], lgb_m["recall_pct"]))
    print(row_fmt.format("F1 Score", f"{rules_m['f1']*100:.2f}%", lr_m["f1_score"], lgb_m["f1_score"]))
    print(row_fmt.format("PR-AUC", "--", lr_m["pr_auc_pct"], lgb_m["pr_auc_pct"]))
    print(row_fmt.format("ROC-AUC", "--", lr_m["roc_auc_pct"], lgb_m["roc_auc_pct"]))
    print(row_fmt.format("False Positive Rate", rules_m["fpr"], lr_m["false_positive_rate"], lgb_m["false_positive_rate"]))
    print(row_fmt.format("False Negative Rate", rules_m["fnr"], lr_m["false_negative_rate"], lgb_m["false_negative_rate"]))
    print(row_fmt.format("Review Rate", rules_m["review_rate"], lr_m["review_rate"], lgb_m["review_rate"]))
    print(row_fmt.format("True Positives (TP)", str(rules_m["true_positives"]), str(lr_m["true_positives"]), str(lgb_m["true_positives"])))
    print(row_fmt.format("False Positives (FP)", str(rules_m["false_positives"]), str(lr_m["false_positives"]), str(lgb_m["false_positives"])))
    print(row_fmt.format("False Negatives (FN)", str(rules_m["false_negatives"]), str(lr_m["false_negatives"]), str(lgb_m["false_negatives"])))
    print(row_fmt.format("Expected Loss (INR)", f"INR {rules_m['expected_loss_inr']:,}", f"INR {lr_m['expected_loss_inr']:,}", f"INR {lgb_m['expected_loss_inr']:,}"))
    print("-" * 80)
    print("FRAUD ARCHETYPE RECALL:")
    print(row_fmt.format("  - Card Testing", rules_m["card_testing_recall"], lr_m["card_testing_recall"], lgb_m["card_testing_recall"]))
    print(row_fmt.format("  - Account Takeover", rules_m["ato_recall"], lr_m["ato_recall"], lgb_m["ato_recall"]))
    print(row_fmt.format("  - Coordinated Rings", rules_m["coordinated_ring_recall"], lr_m["coordinated_ring_recall"], lgb_m["coordinated_ring_recall"]))
    print("=" * 80)

    # 4. Extract Interpretability Features
    lr_coefs = trainer.extract_logistic_coefficients(lr_pipeline)
    lgb_imp = trainer.extract_lightgbm_feature_importance(lgb_model)

    # 5. Export All Artifacts
    paths = trainer.export_all_artifacts(
        lr_pipeline, lgb_model, lr_test, lgb_test,
        lr_tuning, lgb_tuning, lr_coefs, lgb_imp,
        output_dir=out_dir, models_dir=models_dir,
    )
    print("\nArtifacts successfully exported:")
    for name, p in paths.items():
        print(f"  [OK] {p}")


if __name__ == "__main__":
    main()

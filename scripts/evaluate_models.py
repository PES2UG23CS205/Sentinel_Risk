#!/usr/bin/env python3
"""
SentinelRisk — Evaluate Pre-trained ML Models

Usage:
    python scripts/evaluate_models.py [--features-file data/features/transaction_features.csv]
                                      [--models-dir ml/models]

Loads saved Logistic Regression and LightGBM models and evaluates them against the test set.
"""

import sys
import json
import argparse
from pathlib import Path
import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.training.dataset import prepare_ml_dataset
from ml.training.trainer import MLTrainer, CostModelConfig


def main():
    parser = argparse.ArgumentParser(description="Evaluate pre-trained SentinelRisk ML models.")
    parser.add_argument(
        "--features-file",
        type=str,
        default="data/features/transaction_features.csv",
        help="Path to point-in-time features CSV"
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="ml/models",
        help="Directory containing trained model artifacts"
    )
    args = parser.parse_args()

    feat_path = PROJECT_ROOT / args.features_file
    models_dir = PROJECT_ROOT / args.models_dir

    lr_model_path = models_dir / "logistic_regression" / "model.joblib"
    lgb_model_path = models_dir / "lightgbm" / "model.joblib"
    lr_meta_path = models_dir / "logistic_regression" / "metadata.json"
    lgb_meta_path = models_dir / "lightgbm" / "metadata.json"

    if not lr_model_path.exists() or not lgb_model_path.exists():
        print("[!] Error: Model artifacts not found. Run `python scripts/train_models.py` first.")
        sys.exit(1)

    print("=" * 80)
    print("      SENTINELRISK — PRE-TRAINED ML BASELINE EVALUATION")
    print("=" * 80)

    # Load models and metadata
    lr_pipeline = joblib.load(lr_model_path)
    lgb_model = joblib.load(lgb_model_path)

    with open(lr_meta_path, "r") as f:
        lr_meta = json.load(f)
    with open(lgb_meta_path, "r") as f:
        lgb_meta = json.load(f)

    splits = prepare_ml_dataset(feat_path)
    trainer = MLTrainer(splits, CostModelConfig())

    lr_thresh = lr_meta["frozen_threshold"]
    lgb_thresh = lgb_meta["frozen_threshold"]

    lr_test = trainer.evaluate_model_on_test("Logistic Regression", lr_pipeline, lr_thresh, is_pipeline=True)
    lgb_test = trainer.evaluate_model_on_test("LightGBM", lgb_model, lgb_thresh, is_pipeline=False)

    lr_m = lr_test["metrics"]
    lgb_m = lgb_test["metrics"]
    rules_m = trainer.rules_baseline_metrics

    print("\n" + "=" * 80)
    print("                    HELD-OUT TEST SET EVALUATION SUMMARY")
    print("=" * 80)
    row_fmt = "{:<25} {:<18} {:<18} {:<18}"
    print(row_fmt.format("Metric", "Rules (Stage 4)", "Logistic Reg", "LightGBM"))
    print("-" * 80)
    print(row_fmt.format("Precision", f"{rules_m['precision']*100:.2f}%", lr_m["precision_pct"], lgb_m["precision_pct"]))
    print(row_fmt.format("Recall", f"{rules_m['recall']*100:.2f}%", lr_m["recall_pct"], lgb_m["recall_pct"]))
    print(row_fmt.format("F1 Score", f"{rules_m['f1']*100:.2f}%", lr_m["f1_score"], lgb_m["f1_score"]))
    print(row_fmt.format("PR-AUC", "--", lr_m["pr_auc_pct"], lgb_m["pr_auc_pct"]))
    print(row_fmt.format("ROC-AUC", "--", lr_m["roc_auc_pct"], lgb_m["roc_auc_pct"]))
    print(row_fmt.format("Expected Loss (INR)", f"INR {rules_m['expected_loss_inr']:,}", f"INR {lr_m['expected_loss_inr']:,}", f"INR {lgb_m['expected_loss_inr']:,}"))
    print("=" * 80)


if __name__ == "__main__":
    main()

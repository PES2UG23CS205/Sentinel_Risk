"""
SentinelRisk — External Fraud Handbook LightGBM Model Trainer

Trains a dedicated LightGBM risk classifier on the external Fraud Detection Handbook dataset.
Strictly adheres to point-in-time causality, chronological data splitting, and honest evaluation.
"""

import os
import glob
import time
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    precision_recall_curve,
    roc_auc_score,
    auc,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from ml.features.external_features import ExternalFeatureBuilder, EXTERNAL_FEATURE_NAMES


def train_external_model():
    print("=" * 65)
    print("SENTINELRISK — TRAINING EXTERNAL FRAUD HANDBOOK LIGHTGBM MODEL")
    print("=" * 65)

    data_dir = Path("data/external/fraud_handbook/data")
    pkl_files = sorted(glob.glob(str(data_dir / "*.pkl")))
    if not pkl_files:
        raise FileNotFoundError(f"No .pkl files found in {data_dir}")

    print(f"1. Loading {len(pkl_files)} daily pickle files...")
    t0 = time.time()
    dfs = [pd.read_pickle(f) for f in pkl_files]
    full_df = pd.concat(dfs, ignore_index=True)
    full_df = full_df.sort_values(by=["TX_DATETIME", "TRANSACTION_ID"]).reset_index(drop=True)
    total_rows = len(full_df)
    total_frauds = int(full_df["TX_FRAUD"].sum())
    print(f"   Loaded {total_rows:,} transactions ({total_frauds:,} frauds, {total_frauds/total_rows*100:.3f}% prevalence) in {time.time() - t0:.2f}s")

    # 2. Extract point-in-time features sequentially
    print("\n2. Sequential Point-in-Time Feature Extraction (t < T)...")
    t1 = time.time()
    builder = ExternalFeatureBuilder()
    X_features = builder.transform_dataframe(full_df)
    y_target = full_df["TX_FRAUD"].to_numpy(dtype=np.int32)
    print(f"   Extracted {len(EXTERNAL_FEATURE_NAMES)} features across {len(X_features):,} rows in {time.time() - t1:.2f}s")

    # 3. Chronological Train / Validation / Test Split
    # Days 0..119: Train (April 1 - July 29, 2018)
    # Days 120..149: Validation (July 30 - August 28, 2018)
    # Days 150..182: Test (August 29 - September 30, 2018)
    tx_days = full_df["TX_TIME_DAYS"].to_numpy(dtype=np.int64) if "TX_TIME_DAYS" in full_df.columns else np.array([d.dayofyear - full_df['TX_DATETIME'].iloc[0].dayofyear for d in full_df['TX_DATETIME']])

    train_mask = tx_days < 120
    val_mask = (tx_days >= 120) & (tx_days < 150)
    test_mask = tx_days >= 150

    X_train, y_train = X_features[train_mask], y_target[train_mask]
    X_val, y_val = X_features[val_mask], y_target[val_mask]
    X_test, y_test = X_features[test_mask], y_target[test_mask]

    print(f"\n3. Chronological Splits:")
    print(f"   Train split:      {len(X_train):>9,} rows | {int(y_train.sum()):>6,} frauds ({y_train.sum()/len(X_train)*100:.3f}%) | Days 0-119")
    print(f"   Validation split: {len(X_val):>9,} rows | {int(y_val.sum()):>6,} frauds ({y_val.sum()/len(X_val)*100:.3f}%) | Days 120-149")
    print(f"   Test split:       {len(X_test):>9,} rows | {int(y_test.sum()):>6,} frauds ({y_test.sum()/len(X_test)*100:.3f}%) | Days 150-182")

    # 4. Calculate scale_pos_weight strictly on train split
    n_neg = len(y_train) - y_train.sum()
    n_pos = y_train.sum()
    scale_pos_weight = float(n_neg / max(1, n_pos))
    print(f"\n4. Training LightGBM Classifier (scale_pos_weight = {scale_pos_weight:.3f})...")

    model = LGBMClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=20,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbosity=-1,
    )

    t2 = time.time()
    model.fit(X_train, y_train)
    print(f"   Model training complete in {time.time() - t2:.2f}s")

    # 5. Threshold Optimization on Validation Set
    print("\n5. Optimizing Decision Threshold on Validation Set...")
    val_probs = model.predict_proba(X_val)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_val, val_probs)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    best_idx = np.argmax(f1_scores)
    best_threshold = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.50
    # Keep threshold bounded within a sensible risk range [0.05, 0.85]
    chosen_threshold = float(np.clip(best_threshold, 0.05, 0.85))
    print(f"   Optimal validation threshold: {chosen_threshold:.4f} (Max F1: {f1_scores[best_idx]:.4f})")

    # 6. Evaluate on Test Set (Untouched until now)
    print("\n6. Final Evaluation on Untouched Chronological Test Set...")
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= chosen_threshold).astype(int)

    test_prec = float(precision_score(y_test, test_preds, zero_division=0))
    test_rec = float(recall_score(y_test, test_preds, zero_division=0))
    test_f1 = float(f1_score(y_test, test_preds, zero_division=0))
    test_roc_auc = float(roc_auc_score(y_test, test_probs))
    
    p_curve, r_curve, _ = precision_recall_curve(y_test, test_probs)
    test_pr_auc = float(auc(r_curve, p_curve))

    cm = confusion_matrix(y_test, test_preds)
    tn, fp, fn, tp = cm.ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    review_rate = float((tp + fp) / len(y_test))

    print(f"   Precision:     {test_prec*100:.2f}%")
    print(f"   Recall:        {test_rec*100:.2f}%")
    print(f"   F1-Score:      {test_f1*100:.2f}%")
    print(f"   PR-AUC:        {test_pr_auc*100:.2f}%")
    print(f"   ROC-AUC:       {test_roc_auc*100:.2f}%")
    print(f"   FPR:           {fpr*100:.2f}% ({fp} false positives)")
    print(f"   FNR:           {fnr*100:.2f}% ({fn} false negatives)")
    print(f"   Review Rate:   {review_rate*100:.2f}%")

    # 7. Save Model Artifacts
    model_dir = Path("ml/models/external_fraud")
    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_dir / "model.joblib")

    # Feature manifest
    manifest = {
        "model_name": "external_handbook_lightgbm",
        "schema_version": "fraud_handbook_v1",
        "total_features": len(EXTERNAL_FEATURE_NAMES),
        "features": EXTERNAL_FEATURE_NAMES,
    }
    with open(model_dir / "feature_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Feature importances
    importances = model.feature_importances_
    top_features = [
        {"feature": name, "importance": int(imp)}
        for name, imp in sorted(zip(EXTERNAL_FEATURE_NAMES, importances), key=lambda x: x[1], reverse=True)
    ]

    metadata = {
        "model_type": "LGBMClassifier",
        "model_source": "external_handbook_lightgbm",
        "schema": "fraud_handbook_v1",
        "parameters": {
            "n_estimators": 150,
            "learning_rate": 0.05,
            "max_depth": 6,
            "num_leaves": 31,
            "scale_pos_weight": round(scale_pos_weight, 3),
            "random_state": 42,
        },
        "chosen_threshold": round(chosen_threshold, 4),
        "split_info": {
            "train_rows": len(X_train),
            "train_frauds": int(y_train.sum()),
            "val_rows": len(X_val),
            "val_frauds": int(y_val.sum()),
            "test_rows": len(X_test),
            "test_frauds": int(y_test.sum()),
        },
        "test_metrics": {
            "precision": round(test_prec, 4),
            "recall": round(test_rec, 4),
            "f1": round(test_f1, 4),
            "pr_auc": round(test_pr_auc, 4),
            "roc_auc": round(test_roc_auc, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "review_rate": round(review_rate, 4),
            "confusion_matrix": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
            },
        },
        "top_features": top_features,
    }

    with open(model_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # 8. Save Evaluation Reports
    eval_dir = Path("evaluation/external_ml")
    eval_dir.mkdir(parents=True, exist_ok=True)

    with open(eval_dir / "metrics.json", "w") as f:
        json.dump(metadata["test_metrics"], f, indent=2)

    # Confusion matrix CSV
    cm_df = pd.DataFrame(
        [[tn, fp], [fn, tp]],
        index=["Actual Legitimate", "Actual Fraud"],
        columns=["Predicted Legitimate", "Predicted Fraud"],
    )
    cm_df.to_csv(eval_dir / "confusion_matrix.csv")

    # Comparison CSV
    comp_df = pd.DataFrame([
        {"Metric": "Precision", "Value": f"{test_prec*100:.2f}%"},
        {"Metric": "Recall", "Value": f"{test_rec*100:.2f}%"},
        {"Metric": "F1 Score", "Value": f"{test_f1*100:.2f}%"},
        {"Metric": "PR-AUC", "Value": f"{test_pr_auc*100:.2f}%"},
        {"Metric": "ROC-AUC", "Value": f"{test_roc_auc*100:.2f}%"},
        {"Metric": "False Positive Rate", "Value": f"{fpr*100:.2f}%"},
        {"Metric": "False Negative Rate", "Value": f"{fnr*100:.2f}%"},
        {"Metric": "Review Rate", "Value": f"{review_rate*100:.2f}%"},
    ])
    comp_df.to_csv(eval_dir / "comparison.csv", index=False)

    # Markdown Report
    report_md = f"""# External Fraud Detection Handbook — LightGBM Benchmark Report

> Dedicated schema-adaptive risk model trained on 1.75M transactions across 183 daily partitions.

## 1. Split & Dataset Summary
- **Total Transactions**: {total_rows:,}
- **Total Frauds**: {total_frauds:,} ({total_frauds/total_rows*100:.3f}% base prevalence)
- **Train Set (Days 0-119)**: {len(X_train):,} rows ({int(y_train.sum()):,} frauds)
- **Validation Set (Days 120-149)**: {len(X_val):,} rows ({int(y_val.sum()):,} frauds)
- **Test Set (Days 150-182)**: {len(X_test):,} rows ({int(y_test.sum()):,} frauds)

## 2. Model Performance on Untouched Test Set
| Metric | Value |
|---|---|
| **Precision** | **{test_prec*100:.2f}%** |
| **Recall** | **{test_rec*100:.2f}%** |
| **F1-Score** | **{test_f1*100:.2f}%** |
| **PR-AUC** | **{test_pr_auc*100:.2f}%** |
| **ROC-AUC** | **{test_roc_auc*100:.2f}%** |
| **False Positive Rate** | {fpr*100:.2f}% ({fp:,} non-fraud flagged) |
| **False Negative Rate** | {fnr*100:.2f}% ({fn:,} missed frauds) |
| **Review Rate** | {review_rate*100:.2f}% |

## 3. Confusion Matrix
| | Predicted Legitimate | Predicted Fraud |
|---|---|---|
| **Actual Legitimate** | {tn:,} | {fp:,} |
| **Actual Fraud** | {fn:,} | {tp:,} |

## 4. Top 10 Features by Split Importance
{chr(10).join([f"- **{f['feature']}**: {f['importance']} splits" for f in top_features[:10]])}
"""
    with open(eval_dir / "report.md", "w") as f:
        f.write(report_md)

    print(f"\n7. Model artifacts saved to {model_dir}")
    print(f"   Evaluation reports saved to {eval_dir}")
    print("=" * 65)


if __name__ == "__main__":
    train_external_model()

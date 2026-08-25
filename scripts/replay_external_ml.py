"""
SentinelRisk — External Fraud Handbook Replay & ML Inference Demo Script

Evaluates transactions from the Fraud Detection Handbook dataset using the dedicated
schema-adaptive LightGBM model and Stage 7 Policy Engine.

Usage:
    python scripts/replay_external_ml.py --sample-size 1000
    python scripts/replay_external_ml.py --sample-size 5000 --days 10
"""

import argparse
import glob
import json
import time
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score, precision_recall_curve, auc

# Configure UTF-8 stdout encoding for Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.external_features import ExternalFeatureBuilder, EXTERNAL_FEATURE_NAMES
from backend.app.policy.engine import PolicyEngine


def run_external_ml_replay(sample_size: int = 1000, days: int = 5):
    print("\n" + "=" * 75)
    print("  SENTINELRISK — EXTERNAL DATASET REPLAY & SCHEMA-ADAPTIVE ML BENCHMARK")
    print("=" * 75)

    data_dir = Path("data/external/fraud_handbook/data")
    pkl_files = sorted(glob.glob(str(data_dir / "*.pkl")))
    if not pkl_files:
        print(f"Error: No handbook pickle files found in {data_dir}")
        return

    # Load model
    model_path = Path("ml/models/external_fraud/model.joblib")
    if not model_path.exists():
        print(f"Error: External model not found at {model_path}. Train it first.")
        return

    model = joblib.load(model_path)
    policy_engine = PolicyEngine()
    feature_builder = ExternalFeatureBuilder()

    # Load slice
    files_to_load = pkl_files[:days]
    print(f"\n1. Ingesting {len(files_to_load)} partition files ({files_to_load[0][-14:]} to {files_to_load[-1][-14:]})...")
    dfs = [pd.read_pickle(f) for f in files_to_load]
    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values(by=["TX_DATETIME", "TRANSACTION_ID"]).reset_index(drop=True)

    if sample_size > 0 and sample_size < len(df):
        df_eval = df.iloc[:sample_size].copy()
    else:
        df_eval = df.copy()

    total_txns = len(df_eval)
    gt_frauds = int(df_eval["TX_FRAUD"].sum())
    prevalence = (gt_frauds / total_txns) * 100.0

    print(f"   Total Transactions Evaluated: {total_txns:,}")
    print(f"   Ground Truth Frauds:         {gt_frauds:,} ({prevalence:.3f}% base prevalence)")
    print(f"   Active Model:                 external_handbook_lightgbm (LGBMClassifier)")
    print(f"   Active Feature Schema:        fraud_handbook_v1 (24 point-in-time features)")
    print(f"   Signals Omitted Honestly:     23 synthetic-only tokens (device/card identifiers)")

    # 2. Sequential point-in-time feature extraction & inference
    print(f"\n2. Evaluating {total_txns:,} transactions strictly at t < T...")
    t0 = time.time()

    decisions = []
    ml_probs = []
    triggers = []

    for idx, row in df_eval.iterrows():
        # Point-in-time features
        feats = feature_builder.extract_single(
            transaction_id=row["TRANSACTION_ID"],
            timestamp=row["TX_DATETIME"],
            amount=float(row["TX_AMOUNT"]),
            customer_id=row["CUSTOMER_ID"],
            terminal_id=row["TERMINAL_ID"],
            tx_time_seconds=int(row["TX_TIME_SECONDS"]) if "TX_TIME_SECONDS" in row else None,
            update_state=True,
        )

        # LightGBM inference
        feat_df = pd.DataFrame([feats], columns=EXTERNAL_FEATURE_NAMES)
        prob = float(model.predict_proba(feat_df)[:, 1][0])
        ml_probs.append(prob)

        # Policy Engine Evaluation
        dec_record = policy_engine.evaluate(
            transaction_id=row["TRANSACTION_ID"],
            timestamp=str(row["TX_DATETIME"]),
            amount=float(row["TX_AMOUNT"]),
            ml_probability=prob,
            graph_ring_score=0.0,
            graph_ring_candidate=0,
            feature_context={
                "cust_velocity_count_1h": int(feats["cust_velocity_1h"]),
                "cust_amount_to_mean_ratio": round(feats["cust_amount_ratio"], 2),
            },
        )
        decisions.append(dec_record.decision.value if hasattr(dec_record.decision, "value") else str(dec_record.decision))
        triggers.append(dec_record.primary_trigger or "APPROVED_BASELINE")

    elapsed = time.time() - t0
    throughput = total_txns / max(0.001, elapsed)

    # 3. Decision Breakdown
    n_approve = sum(1 for d in decisions if d == "APPROVE")
    n_review = sum(1 for d in decisions if d == "REVIEW")
    n_hold = sum(1 for d in decisions if d == "HOLD")

    # 4. Evaluation Metrics
    y_true = df_eval["TX_FRAUD"].to_numpy(dtype=int)
    y_pred_hold = np.array([1 if d in ("REVIEW", "HOLD") else 0 for d in decisions])
    y_probs = np.array(ml_probs)

    prec = float(precision_score(y_true, y_pred_hold, zero_division=0))
    rec = float(recall_score(y_true, y_pred_hold, zero_division=0))
    f1 = float(f1_score(y_true, y_pred_hold, zero_division=0))
    
    try:
        roc_auc = float(roc_auc_score(y_true, y_probs)) if len(np.unique(y_true)) > 1 else 1.0
        p_c, r_c, _ = precision_recall_curve(y_true, y_probs)
        pr_auc = float(auc(r_c, p_c))
    except Exception:
        roc_auc, pr_auc = 0.0, 0.0

    cm = confusion_matrix(y_true, y_pred_hold)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn, fp, fn, tp = len(y_true) - gt_frauds, 0, gt_frauds, 0

    print(f"\n3. Execution Summary:")
    print(f"   Elapsed Time:     {elapsed:.3f} s ({throughput:,.0f} txns/sec)")
    print(f"   Avg Decision Lat: {(elapsed/total_txns)*1000:.3f} ms")

    print(f"\n4. Policy Decision Distribution:")
    print(f"   [APPROVE]:        {n_approve:>6,} ({n_approve/total_txns*100:.2f}%)")
    print(f"   [REVIEW]:         {n_review:>6,} ({n_review/total_txns*100:.2f}%)")
    print(f"   [HOLD]:           {n_hold:>6,} ({n_hold/total_txns*100:.2f}%)")

    print(f"\n5. Detection Performance (Ground Truth Comparison):")
    print(f"   Precision:        {prec*100:.2f}%")
    print(f"   Recall:           {rec*100:.2f}% ({tp}/{gt_frauds} frauds intercepted)")
    print(f"   F1-Score:         {f1*100:.2f}%")
    print(f"   PR-AUC:           {pr_auc*100:.2f}%")
    print(f"   ROC-AUC:          {roc_auc*100:.2f}%")
    print(f"   False Positives:  {fp:,} (non-fraud interventions)")
    print(f"   False Negatives:  {fn:,} (missed frauds)")

    # 6. Sample Decision Traces
    print(f"\n6. Sample Decision Traces:")
    print(f"   {'TXN_ID':<10} | {'AMOUNT':<10} | {'ML PROB':<8} | {'DECISION':<8} | {'GT':<6} | {'PRIMARY TRIGGER'}")
    print("   " + "-" * 70)
    for i in range(min(8, total_txns)):
        t_id = df_eval.iloc[i]["TRANSACTION_ID"]
        amt = f"€{df_eval.iloc[i]['TX_AMOUNT']:.2f}"
        prob_str = f"{ml_probs[i]*100:.1f}%"
        dec = decisions[i]
        gt = "FRAUD" if df_eval.iloc[i]["TX_FRAUD"] == 1 else "LEGIT"
        trig = triggers[i]
        print(f"   {t_id:<10} | {amt:<10} | {prob_str:<8} | {dec:<8} | {gt:<6} | {trig}")

    print("=" * 75 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelRisk External Dataset ML Replay")
    parser.add_argument("--sample-size", type=int, default=1000, help="Number of transactions to replay")
    parser.add_argument("--days", type=int, default=5, help="Number of daily partition files to load")
    args = parser.parse_args()

    run_external_ml_replay(sample_size=args.sample_size, days=args.days)

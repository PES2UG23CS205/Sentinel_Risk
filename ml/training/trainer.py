"""
SentinelRisk — Supervised Machine Learning Baselines & Benchmarking

Trains and evaluates:
  1. Logistic Regression (Linear, interpretable, standardized + one-hot encoded, balanced class weights)
  2. LightGBM (Non-linear gradient-boosted decision trees, scale_pos_weight class weighting)

Enforces:
  - Exact Stage 4 chronological split (70% Train, 15% Val, 15% Test)
  - Fit-on-train only preprocessing
  - Validation-only threshold optimization (minimizing Expected Financial Loss)
  - Single-pass evaluation on sacred held-out Test set
  - Direct comparison with frozen Stage 4 rules benchmark
  - Archetype recall breakdown (ATO, Card Testing, Coordinated Rings)
  - Feature importances and Logistic coefficients
  - Probability calibration analysis
  - Error analysis sampling
"""

import json
import csv
from pathlib import Path
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
import joblib
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    average_precision_score,
    roc_auc_score,
)

from ml.training.dataset import DatasetSplits, prepare_ml_dataset
from ml.training.preprocessing import build_logistic_preprocessor, CATEGORICAL_COLS


@dataclass
class CostModelConfig:
    """Business cost parameters matching Stage 4 exactly."""
    false_positive_cost: float = 150.0  # INR per false positive (friction & triage)
    review_cost: float = 50.0          # INR per review action
    fraud_loss_multiplier: float = 1.0  # 100% loss on unprevented fraud amounts


class MLTrainer:
    """Trains, optimizes, and benchmarks ML baselines against Stage 4 rules."""

    def __init__(
        self,
        splits: DatasetSplits,
        cost_config: CostModelConfig | None = None,
        random_seed: int = 42,
    ):
        self.splits = splits
        self.cost_config = cost_config or CostModelConfig()
        self.seed = random_seed

        # Frozen Stage 4 Rules Baseline results for direct comparison
        self.rules_baseline_metrics = {
            "model_name": "Rules Baseline (Stage 4 Frozen)",
            "precision": 0.4444,
            "recall": 0.2137,
            "f1": 0.2887,
            "pr_auc": None,
            "roc_auc": None,
            "fpr": "0.35%",
            "fnr": "78.63%",
            "review_rate": "0.62%",
            "true_positives": 28,
            "false_positives": 35,
            "true_negatives": 10013,
            "false_negatives": 103,
            "expected_loss_inr": 641079.22,
            "fraud_loss_prevented_inr": 30865.41,
            "ato_recall": "3.00%",
            "card_testing_recall": "80.65%",
            "coordinated_ring_recall": "0.00%",
        }

    def train_logistic_regression(self) -> Pipeline:
        """Train Logistic Regression pipeline on Train partition."""
        preprocessor = build_logistic_preprocessor(self.splits.feature_names)
        clf = LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            C=1.0,
            random_state=self.seed,
            solver="lbfgs",
        )
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", clf),
        ])
        pipeline.fit(self.splits.X_train, self.splits.y_train)
        return pipeline

    def train_lightgbm(self) -> LGBMClassifier:
        """Train LightGBM gradient-boosted decision tree on Train partition."""
        clf = LGBMClassifier(
            scale_pos_weight=self.splits.scale_pos_weight,
            n_estimators=150,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=31,
            min_child_samples=20,
            random_state=self.seed,
            verbose=-1,
            n_jobs=-1,
        )
        clf.fit(self.splits.X_train, self.splits.y_train)
        return clf

    def optimize_threshold_on_validation(
        self,
        model,
        is_pipeline: bool = False,
    ) -> tuple[float, list[dict]]:
        """
        Scan probability thresholds on Validation partition ONLY.
        Select the operating threshold minimizing Expected Financial Loss.
        """
        if is_pipeline:
            val_probs = model.predict_proba(self.splits.X_val)[:, 1]
        else:
            val_probs = model.predict_proba(self.splits.X_val)[:, 1]

        y_true = self.splits.y_val
        amounts = self.splits.amounts_val

        candidate_thresholds = np.linspace(0.05, 0.95, 19)
        tuning_results = []
        best_thresh = 0.5
        min_loss = float("inf")

        for thresh in candidate_thresholds:
            t = round(float(thresh), 2)
            y_pred = (val_probs >= t).astype(int)
            metrics = self._calculate_metrics(y_true, y_pred, val_probs, amounts)
            metrics["threshold"] = t
            tuning_results.append(metrics)

            if metrics["expected_loss_inr"] < min_loss:
                min_loss = metrics["expected_loss_inr"]
                best_thresh = t

        return best_thresh, tuning_results

    def evaluate_model_on_test(
        self,
        model_name: str,
        model,
        frozen_threshold: float,
        is_pipeline: bool = False,
    ) -> dict:
        """
        Evaluate frozen model pipeline and threshold on sacred held-out Test set.
        """
        test_probs = model.predict_proba(self.splits.X_test)[:, 1]
        y_true = self.splits.y_test
        amounts = self.splits.amounts_test
        archetypes = self.splits.archetypes_test

        y_pred = (test_probs >= frozen_threshold).astype(int)
        metrics = self._calculate_metrics(y_true, y_pred, test_probs, amounts)
        metrics["model_name"] = model_name
        metrics["frozen_threshold"] = frozen_threshold

        # PR-AUC and ROC-AUC
        pr_auc = float(average_precision_score(y_true, test_probs))
        roc_auc = float(roc_auc_score(y_true, test_probs))
        metrics["pr_auc"] = round(pr_auc, 4)
        metrics["roc_auc"] = round(roc_auc, 4)
        metrics["pr_auc_pct"] = f"{pr_auc*100:.2f}%"
        metrics["roc_auc_pct"] = f"{roc_auc*100:.2f}%"

        # Archetype Breakdown
        archetype_perf = {}
        for arch in ["account_takeover", "card_testing", "coordinated_ring"]:
            mask = archetypes == arch
            total_cases = int(mask.sum())
            caught_cases = int(((mask) & (y_pred == 1)).sum())
            recall = caught_cases / total_cases if total_cases > 0 else 0.0
            archetype_perf[arch] = {
                "total_cases": total_cases,
                "caught_cases": caught_cases,
                "missed_cases": total_cases - caught_cases,
                "recall": f"{recall*100:.2f}%",
            }
        metrics["ato_recall"] = archetype_perf["account_takeover"]["recall"]
        metrics["card_testing_recall"] = archetype_perf["card_testing"]["recall"]
        metrics["coordinated_ring_recall"] = archetype_perf["coordinated_ring"]["recall"]

        # Probability Calibration Analysis (10 buckets)
        calibration_buckets = []
        bucket_edges = np.linspace(0.0, 1.0, 11)
        for i in range(len(bucket_edges) - 1):
            low, high = bucket_edges[i], bucket_edges[i+1]
            b_mask = (test_probs >= low) & (test_probs < high) if i < 9 else (test_probs >= low) & (test_probs <= high)
            b_count = int(b_mask.sum())
            if b_count > 0:
                mean_pred = float(np.mean(test_probs[b_mask]))
                actual_fraud_rate = float(np.mean(y_true[b_mask]))
            else:
                mean_pred = (low + high) / 2.0
                actual_fraud_rate = 0.0

            calibration_buckets.append({
                "bucket": f"[{low:.1f}, {high:.1f})",
                "count": b_count,
                "mean_predicted_prob": f"{mean_pred*100:.2f}%",
                "observed_fraud_rate": f"{actual_fraud_rate*100:.2f}%",
            })

        # Systematic Error Analysis Sampling
        # False Positives
        fp_mask = (y_true == 0) & (y_pred == 1)
        fp_indices = np.where(fp_mask)[0][:5]
        fp_samples = []
        for idx in fp_indices:
            row_dict = self.splits.X_test.iloc[idx].to_dict()
            fp_samples.append({
                "amount": float(amounts[idx]),
                "predicted_prob": round(float(test_probs[idx]), 4),
                "cust_amount_to_mean_ratio": round(float(row_dict.get("cust_amount_to_mean_ratio", 1.0)), 2),
                "velocity_txn_count_1h": int(row_dict.get("velocity_txn_count_1h", 0)),
                "device_is_new_for_cust": int(row_dict.get("device_is_new_for_cust", 0)),
            })

        # False Negatives
        fn_mask = (y_true == 1) & (y_pred == 0)
        fn_indices = np.where(fn_mask)[0][:5]
        fn_samples = []
        for idx in fn_indices:
            row_dict = self.splits.X_test.iloc[idx].to_dict()
            fn_samples.append({
                "amount": float(amounts[idx]),
                "predicted_prob": round(float(test_probs[idx]), 4),
                "fraud_archetype": str(archetypes[idx]),
                "cust_amount_to_mean_ratio": round(float(row_dict.get("cust_amount_to_mean_ratio", 1.0)), 2),
                "velocity_txn_count_1h": int(row_dict.get("velocity_txn_count_1h", 0)),
                "device_is_new_for_cust": int(row_dict.get("device_is_new_for_cust", 0)),
            })

        return {
            "metrics": metrics,
            "archetype_performance": archetype_perf,
            "calibration": calibration_buckets,
            "error_analysis": {
                "false_positives_sample": fp_samples,
                "false_negatives_sample": fn_samples,
            },
        }

    def extract_logistic_coefficients(self, pipeline: Pipeline) -> list[dict]:
        """Extract signed feature coefficients from fitted Logistic Regression pipeline."""
        clf = pipeline.named_steps["classifier"]
        preprocessor = pipeline.named_steps["preprocessor"]

        # Get transformed feature names
        cat_features = preprocessor.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_COLS)
        continuous_cols = [
            c for c in self.splits.feature_names
            if c not in CATEGORICAL_COLS and c not in [
                "is_weekend", "is_night", "cust_is_first_txn", "device_is_new_for_cust"
            ]
        ]
        binary_cols = ["is_weekend", "is_night", "cust_is_first_txn", "device_is_new_for_cust"]
        all_feature_names = list(continuous_cols) + list(cat_features) + list(binary_cols)

        coefs = clf.coef_[0]
        coef_list = []
        for name, val in zip(all_feature_names, coefs):
            coef_list.append({
                "feature": name,
                "coefficient": round(float(val), 4),
                "abs_coefficient": round(float(abs(val)), 4),
                "direction": "Increases Risk (Positive)" if val > 0 else "Decreases Risk (Negative)",
            })

        coef_list.sort(key=lambda x: x["abs_coefficient"], reverse=True)
        return coef_list

    def extract_lightgbm_feature_importance(self, model: LGBMClassifier) -> list[dict]:
        """Extract split and gain feature importances from LightGBM."""
        gain_imp = model.booster_.feature_importance(importance_type="gain")
        split_imp = model.booster_.feature_importance(importance_type="split")

        importances = []
        for name, g, s in zip(self.splits.feature_names, gain_imp, split_imp):
            importances.append({
                "feature": name,
                "gain_importance": round(float(g), 2),
                "split_importance": int(s),
            })
        importances.sort(key=lambda x: x["gain_importance"], reverse=True)
        return importances

    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        probs: np.ndarray,
        amounts: np.ndarray,
    ) -> dict:
        """Compute precision, recall, F1, FPR, FNR, review rate, and business loss."""
        tp = int(((y_true == 1) & (y_pred == 1)).sum())
        fp = int(((y_true == 0) & (y_pred == 1)).sum())
        tn = int(((y_true == 0) & (y_pred == 0)).sum())
        fn = int(((y_true == 1) & (y_pred == 0)).sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        review_rate = (tp + fp) / len(y_true) if len(y_true) > 0 else 0.0

        # Cost calculations
        fn_mask = (y_true == 1) & (y_pred == 0)
        tp_mask = (y_true == 1) & (y_pred == 1)

        fn_fraud_loss = float(np.sum(amounts[fn_mask]) * self.cost_config.fraud_loss_multiplier)
        tp_fraud_avoided = float(np.sum(amounts[tp_mask]) * self.cost_config.fraud_loss_multiplier)
        fp_friction_cost = float(fp * self.cost_config.false_positive_cost)
        review_overhead_cost = float((tp + fp) * self.cost_config.review_cost)

        expected_loss = fn_fraud_loss + fp_friction_cost + review_overhead_cost

        return {
            "total_transactions": len(y_true),
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "precision_pct": f"{precision*100:.2f}%",
            "recall_pct": f"{recall*100:.2f}%",
            "f1_score": f"{f1*100:.2f}%",
            "false_positive_rate": f"{fpr*100:.2f}%",
            "false_negative_rate": f"{fnr*100:.2f}%",
            "review_rate": f"{review_rate*100:.2f}%",
            "fn_fraud_loss_inr": round(fn_fraud_loss, 2),
            "tp_fraud_avoided_inr": round(tp_fraud_avoided, 2),
            "fp_friction_cost_inr": round(fp_friction_cost, 2),
            "review_overhead_cost_inr": round(review_overhead_cost, 2),
            "expected_loss_inr": round(expected_loss, 2),
        }

    def export_all_artifacts(
        self,
        lr_pipeline: Pipeline,
        lgb_model: LGBMClassifier,
        lr_results: dict,
        lgb_results: dict,
        lr_tuning: list[dict],
        lgb_tuning: list[dict],
        lr_coefs: list[dict],
        lgb_imp: list[dict],
        output_dir: str | Path = "evaluation/ml_baselines",
        models_dir: str | Path = "ml/models",
    ) -> dict:
        """Export serialized models, JSON metadata, comparison tables, and markdown report."""
        out_base = Path(output_dir)
        models_base = Path(models_dir)

        out_base.mkdir(parents=True, exist_ok=True)
        (out_base / "logistic_regression").mkdir(exist_ok=True)
        (out_base / "lightgbm").mkdir(exist_ok=True)
        (models_base / "logistic_regression").mkdir(parents=True, exist_ok=True)
        (models_base / "lightgbm").mkdir(parents=True, exist_ok=True)

        # 1. Save Serialized Models
        joblib.dump(lr_pipeline, models_base / "logistic_regression" / "model.joblib")
        joblib.dump(lgb_model, models_base / "lightgbm" / "model.joblib")
        lgb_model.booster_.save_model(str(models_base / "lightgbm" / "model.txt"))

        # 2. Save Model Metadata
        lr_meta = {
            "model_type": "LogisticRegression",
            "package": "scikit-learn",
            "version": "1.9.0",
            "parameters": {"C": 1.0, "class_weight": "balanced", "solver": "lbfgs", "random_state": self.seed},
            "frozen_threshold": lr_results["metrics"]["frozen_threshold"],
            "test_metrics": lr_results["metrics"],
            "split_info": self.splits.split_info,
            "top_coefficients": lr_coefs[:10],
        }
        with open(models_base / "logistic_regression" / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(lr_meta, f, indent=2)

        lgb_meta = {
            "model_type": "LGBMClassifier",
            "package": "lightgbm",
            "version": "4.7.0",
            "parameters": {
                "scale_pos_weight": round(self.splits.scale_pos_weight, 4),
                "n_estimators": 150,
                "learning_rate": 0.05,
                "max_depth": 6,
                "num_leaves": 31,
                "min_child_samples": 20,
                "random_state": self.seed,
            },
            "frozen_threshold": lgb_results["metrics"]["frozen_threshold"],
            "test_metrics": lgb_results["metrics"],
            "split_info": self.splits.split_info,
            "top_features_by_gain": lgb_imp[:10],
        }
        with open(models_base / "lightgbm" / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(lgb_meta, f, indent=2)

        # 3. Save Evaluation JSONs
        with open(out_base / "logistic_regression" / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(lr_results, f, indent=2)

        with open(out_base / "lightgbm" / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(lgb_results, f, indent=2)

        # 4. Save Comparison CSV
        comparison_rows = [
            self.rules_baseline_metrics,
            lr_results["metrics"],
            lgb_results["metrics"],
        ]
        comp_csv_path = out_base / "comparison.csv"
        with open(comp_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Model", "Precision", "Recall", "F1 Score", "PR-AUC", "ROC-AUC",
                "FPR", "FNR", "Review Rate", "TP", "FP", "TN", "FN", "Expected Loss (INR)", "Fraud Loss Prevented (INR)"
            ])
            for r in comparison_rows:
                fpr = r.get("false_positive_rate", r.get("fpr", "--"))
                fnr = r.get("false_negative_rate", r.get("fnr", "--"))
                rev = r.get("review_rate", "--")
                prec = r.get("precision_pct", f"{r['precision']*100:.2f}%" if r.get("precision") is not None else "--")
                rec = r.get("recall_pct", f"{r['recall']*100:.2f}%" if r.get("recall") is not None else "--")
                f1_str = r.get("f1_score", f"{r['f1']*100:.2f}%" if r.get("f1") is not None else "--")
                pr_auc_str = r.get("pr_auc_pct", f"{r['pr_auc']*100:.2f}%" if r.get("pr_auc") is not None else "--")
                roc_auc_str = r.get("roc_auc_pct", f"{r['roc_auc']*100:.2f}%" if r.get("roc_auc") is not None else "--")
                writer.writerow([
                    r["model_name"], prec, rec, f1_str, pr_auc_str, roc_auc_str,
                    fpr, fnr, rev,
                    r["true_positives"], r["false_positives"], r["true_negatives"], r["false_negatives"],
                    r["expected_loss_inr"], r.get("tp_fraud_avoided_inr", r.get("fraud_loss_prevented_inr")),
                ])

        # 5. Save Comparison JSON
        with open(out_base / "comparison.json", "w", encoding="utf-8") as f:
            json.dump({
                "rules_baseline": self.rules_baseline_metrics,
                "logistic_regression": lr_results["metrics"],
                "lightgbm": lgb_results["metrics"],
            }, f, indent=2)

        # 6. Generate Markdown Report
        report_path = out_base / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self._generate_markdown_report(lr_results, lgb_results, lr_coefs, lgb_imp))

        return {
            "comparison_csv": comp_csv_path,
            "report_md": report_path,
        }

    def _generate_markdown_report(
        self,
        lr_results: dict,
        lgb_results: dict,
        lr_coefs: list[dict],
        lgb_imp: list[dict],
    ) -> str:
        rules = self.rules_baseline_metrics
        lr = lr_results["metrics"]
        lgb = lgb_results["metrics"]
        split = self.splits.split_info

        lr_loss_diff = lr["expected_loss_inr"] - rules["expected_loss_inr"]
        lr_loss_pct = (lr_loss_diff / rules["expected_loss_inr"]) * 100

        lgb_loss_diff = lgb["expected_loss_inr"] - rules["expected_loss_inr"]
        lgb_loss_pct = (lgb_loss_diff / rules["expected_loss_inr"]) * 100

        md = f"""# SentinelRisk — Stage 5: Machine Learning Baselines Report

## 1. Executive Summary & Controlled Benchmark

We trained and evaluated **Logistic Regression** and **LightGBM** on the exact same point-in-time features and chronological split as the frozen Stage 4 Rules Baseline.

### Definitive Test Performance Comparison:

| Metric | Rules Baseline (Stage 4) | Logistic Regression | LightGBM |
|---|:---:|:---:|:---:|
| **Precision** | {rules['precision']*100:.2f}% | {lr['precision_pct']} | {lgb['precision_pct']} |
| **Recall** | {rules['recall']*100:.2f}% | {lr['recall_pct']} | {lgb['recall_pct']} |
| **F1 Score** | {rules['f1']*100:.2f}% | {lr['f1_score']} | {lgb['f1_score']} |
| **PR-AUC** | -- | {lr['pr_auc_pct']} | {lgb['pr_auc_pct']} |
| **ROC-AUC** | -- | {lr['roc_auc_pct']} | {lgb['roc_auc_pct']} |
| **False Positive Rate (FPR)** | {rules['fpr']} | {lr['false_positive_rate']} | {lgb['false_positive_rate']} |
| **False Negative Rate (FNR)** | {rules['fnr']} | {lr['false_negative_rate']} | {lgb['false_negative_rate']} |
| **Review Rate** | {rules['review_rate']} | {lr['review_rate']} | {lgb['review_rate']} |
| **Expected Financial Loss** | **INR {rules['expected_loss_inr']:,}** | **INR {lr['expected_loss_inr']:,}** | **INR {lgb['expected_loss_inr']:,}** |
| **Loss Reduction vs Rules** | Baseline (0.0%) | {f"{-lr_loss_pct:.2f}% reduction" if lr_loss_diff < 0 else f"+{lr_loss_pct:.2f}% increase"} | {f"{-lgb_loss_pct:.2f}% reduction" if lgb_loss_diff < 0 else f"+{lgb_loss_pct:.2f}% increase"} |

---

## 2. Fraud Archetype Recall Breakdown (Test Set)

| Fraud Archetype | Rules Recall | Logistic Regression Recall | LightGBM Recall | Key Architectural Insight |
|---|:---:|:---:|:---:|---|
| **Card Testing Velocity** | {rules['card_testing_recall']} | {lr['card_testing_recall']} | {lgb['card_testing_recall']} | Strong across both rules and ML due to prominent velocity spike signals. |
| **Account Takeover (ATO)** | {rules['ato_recall']} | {lr['ato_recall']} | {lgb['ato_recall']} | ML captures non-linear interactions across device novelty, spending ratios, and customer age. |
| **Coordinated Abuse Rings** | {rules['coordinated_ring_recall']} | {lr['coordinated_ring_recall']} | {lgb['coordinated_ring_recall']} | Blind spot for single-transaction classifiers; motivates graph detection in Stage 6. |

---

## 3. Top Feature Insights

### LightGBM Top 5 Features (by Gain Importance):
"""
        for i, f_info in enumerate(lgb_imp[:5], 1):
            md += f"{i}. **{f_info['feature']}** (Gain: {f_info['gain_importance']:,})\n"

        md += f"""
### Logistic Regression Top 5 Positive Risk Coefficients (Increase Log-Odds of Fraud):
"""
        for i, c_info in enumerate([c for c in lr_coefs if c["coefficient"] > 0][:5], 1):
            md += f"{i}. **{c_info['feature']}** (+{c_info['coefficient']:.4f})\n"

        md += f"""
---

## 4. Business Cost & Financial Impact
- **Rules Baseline Expected Loss**: INR {rules['expected_loss_inr']:,}
- **Logistic Regression Expected Loss**: INR {lr['expected_loss_inr']:,}
- **LightGBM Expected Loss**: INR {lgb['expected_loss_inr']:,}
- **Fraud Prevented by LightGBM**: **INR {lgb['tp_fraud_avoided_inr']:,}**
"""
        return md

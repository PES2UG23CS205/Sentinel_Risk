"""
SentinelRisk — Rules Baseline Evaluator & Benchmark Pipeline

Executes chronological train/validation/test evaluation:
  1. Strict chronological 70/15/15 dataset split (Train, Validation, Held-out Test)
  2. Threshold tuning using Training and Validation sets only
  3. Freezing selected baseline configuration
  4. Final evaluation on the untouched Held-out Test set
  5. Cost modeling (Expected Loss, FP friction cost, FN fraud loss, Review triage cost)
  6. Granular fraud archetype breakdown (ATO, Card Testing, Coordinated Rings)
  7. Systematic error analysis for False Positives and False Negatives
"""

import json
import csv
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from backend.app.policy.config import RuleConfig
from backend.app.policy.rules import RulesEngine


class RulesBaselineEvaluator:
    """Evaluates the rules-only risk baseline on temporally partitioned data."""

    def __init__(self, df: pd.DataFrame, config: RuleConfig | None = None):
        self.df = df.copy()
        self.config = config or RuleConfig()

        # Target label column (using clean synthetic ground truth)
        self.target_col = "is_fraud_ground_truth"

        # Split data chronologically
        self._prepare_splits()

    def _prepare_splits(self):
        """Split dataframe into Train (70%), Validation (15%), and Test (15%) in chronological order."""
        # Ensure sorting by timestamp
        self.df = self.df.sort_values("timestamp").reset_index(drop=True)
        n = len(self.df)

        idx_train = int(n * self.config.train_fraction)
        idx_val = int(n * (self.config.train_fraction + self.config.val_fraction))

        self.train_df = self.df.iloc[:idx_train].copy()
        self.val_df = self.df.iloc[idx_train:idx_val].copy()
        self.test_df = self.df.iloc[idx_val:].copy()

        train_len = max(1, len(self.train_df))
        val_len = max(1, len(self.val_df))
        test_len = max(1, len(self.test_df))

        self.split_info = {
            "train": {
                "count": len(self.train_df),
                "fraud_count": int(self.train_df[self.target_col].sum()) if len(self.train_df) > 0 else 0,
                "fraud_prevalence": f"{(self.train_df[self.target_col].sum() / train_len)*100:.2f}%" if len(self.train_df) > 0 else "0.00%",
                "start_date": str(self.train_df["timestamp"].min()) if len(self.train_df) > 0 else "",
                "end_date": str(self.train_df["timestamp"].max()) if len(self.train_df) > 0 else "",
            },
            "validation": {
                "count": len(self.val_df),
                "fraud_count": int(self.val_df[self.target_col].sum()) if len(self.val_df) > 0 else 0,
                "fraud_prevalence": f"{(self.val_df[self.target_col].sum() / val_len)*100:.2f}%" if len(self.val_df) > 0 else "0.00%",
                "start_date": str(self.val_df["timestamp"].min()) if len(self.val_df) > 0 else "",
                "end_date": str(self.val_df["timestamp"].max()) if len(self.val_df) > 0 else "",
            },
            "test": {
                "count": len(self.test_df),
                "fraud_count": int(self.test_df[self.target_col].sum()) if len(self.test_df) > 0 else 0,
                "fraud_prevalence": f"{(self.test_df[self.target_col].sum() / test_len)*100:.2f}%" if len(self.test_df) > 0 else "0.00%",
                "start_date": str(self.test_df["timestamp"].min()) if len(self.test_df) > 0 else "",
                "end_date": str(self.test_df["timestamp"].max()) if len(self.test_df) > 0 else "",
            },
        }

    def tune_thresholds_on_validation(self) -> list[dict]:
        """
        Evaluate candidate rule-score thresholds strictly on the Validation set.
        The Test set remains untouched during this process.
        """
        engine = RulesEngine(self.config)
        val_eval = engine.evaluate_dataframe(self.val_df)
        y_true = val_eval[self.target_col].astype(int).values
        amounts = val_eval["amount"].values
        scores = val_eval["rule_score"].values

        candidate_thresholds = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        results = []

        for thresh in candidate_thresholds:
            y_pred = (scores >= thresh).astype(int)
            decisions = np.where(scores >= thresh, "REVIEW", "APPROVE")
            metrics = self._calculate_metrics(y_true, y_pred, amounts, decisions)
            metrics["threshold"] = thresh
            results.append(metrics)

        return results

    def evaluate_test_set(self, selected_threshold: float = 3.0) -> dict:
        """
        Evaluate the frozen baseline configuration once on the held-out Test set.
        """
        # Apply frozen threshold
        frozen_config = RuleConfig(
            flag_score_threshold=selected_threshold,
            threshold_review=selected_threshold,
            threshold_hold=selected_threshold + 2.0,
        )
        engine = RulesEngine(frozen_config)
        test_eval = engine.evaluate_dataframe(self.test_df)

        y_true = test_eval[self.target_col].astype(int).values
        amounts = test_eval["amount"].values
        scores = test_eval["rule_score"].values
        y_pred = test_eval["is_flagged"].astype(int).values
        decisions = test_eval["decision"].values

        test_metrics = self._calculate_metrics(y_true, y_pred, amounts, decisions)
        test_metrics["frozen_threshold"] = selected_threshold

        # Rule Contribution Analysis
        rule_cols = [
            ("rule_1_cust_amount_anomaly", "Customer Amount Anomaly"),
            ("rule_2_cust_velocity", "Customer Velocity"),
            ("rule_3_device_novelty", "Device Novelty Compound"),
            ("rule_4_pi_velocity", "Payment Instrument Velocity"),
            ("rule_5_merchant_anomaly", "Merchant Relative Anomaly"),
            ("rule_6_off_hour_anomaly", "Off-Hour Anomaly"),
        ]
        rule_contributions = []
        for col_name, display_name in rule_cols:
            triggered = test_eval[col_name].astype(bool)
            trig_count = int(triggered.sum())
            trig_rate = trig_count / len(test_eval) if len(test_eval) > 0 else 0.0

            # Precision when rule triggers
            tp_rule = int((triggered & (y_true == 1)).sum())
            prec_rule = tp_rule / trig_count if trig_count > 0 else 0.0

            rule_contributions.append({
                "rule_name": col_name,
                "display_name": display_name,
                "trigger_count": trig_count,
                "trigger_rate": f"{trig_rate*100:.2f}%",
                "true_positives": tp_rule,
                "precision_when_triggered": f"{prec_rule*100:.2f}%",
            })

        # Fraud Archetype Breakdown on Test Set
        archetype_performance = {}
        for arch in ["account_takeover", "card_testing", "coordinated_ring"]:
            arch_mask = (test_eval["fraud_archetype"] == arch).values
            total_arch = int(arch_mask.sum())
            caught_arch = int((arch_mask & (y_pred == 1)).sum())
            recall_arch = caught_arch / total_arch if total_arch > 0 else 0.0

            archetype_performance[arch] = {
                "total_cases": total_arch,
                "caught_cases": caught_arch,
                "missed_cases": total_arch - caught_arch,
                "recall": f"{recall_arch*100:.2f}%",
            }

        # Systematic Error Analysis Sampling
        # False Positives (Legitimate flagged as fraud)
        fp_mask = (y_true == 0) & (y_pred == 1)
        fp_sample = test_eval[fp_mask].head(5)[
            ["transaction_id", "amount", "cust_amount_to_mean_ratio", "velocity_txn_count_1h", "device_is_new_for_cust", "rule_score", "decision"]
        ].to_dict(orient="records")

        # False Negatives (Fraud missed by rules)
        fn_mask = (y_true == 1) & (y_pred == 0)
        fn_sample = test_eval[fn_mask].head(5)[
            ["transaction_id", "amount", "fraud_archetype", "cust_amount_to_mean_ratio", "velocity_txn_count_1h", "device_is_new_for_cust", "rule_score", "decision"]
        ].to_dict(orient="records")

        return {
            "metrics": test_metrics,
            "rule_contributions": rule_contributions,
            "archetype_performance": archetype_performance,
            "error_analysis": {
                "false_positives_sample": fp_sample,
                "false_negatives_sample": fn_sample,
            },
            "split_info": self.split_info,
        }

    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        amounts: np.ndarray,
        decisions: np.ndarray,
    ) -> dict:
        """Calculate classification and business cost metrics."""
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

        # Financial cost calculations
        fn_mask = (y_true == 1) & (y_pred == 0)
        tp_mask = (y_true == 1) & (y_pred == 1)

        fn_fraud_loss = float(np.sum(amounts[fn_mask]) * self.config.fraud_loss_multiplier)
        tp_fraud_avoided = float(np.sum(amounts[tp_mask]) * self.config.fraud_loss_multiplier)

        fp_friction_cost = float(fp * self.config.false_positive_cost)
        review_count = int((decisions == "REVIEW").sum())
        review_overhead_cost = float(review_count * self.config.review_cost)

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

    def export_artifacts(self, val_tuning: list[dict], test_results: dict, output_dir: str | Path) -> dict[str, Path]:
        """Export metrics, threshold comparisons, and markdown report."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        paths = {}

        # 1. metrics.json
        metrics_path = out_path / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(test_results, f, indent=2)
        paths["metrics"] = metrics_path

        # 2. threshold_comparison.csv
        thresh_path = out_path / "threshold_comparison.csv"
        with open(thresh_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["threshold", "precision", "recall", "f1", "review_rate", "expected_loss_inr", "fraud_loss_inr", "fp_cost_inr"])
            for r in val_tuning:
                writer.writerow([
                    r["threshold"], r["precision_pct"], r["recall_pct"],
                    r["f1_score"], r["review_rate"], r["expected_loss_inr"],
                    r["fn_fraud_loss_inr"], r["fp_friction_cost_inr"],
                ])
        paths["threshold_comparison"] = thresh_path

        # 3. cost_analysis.csv
        cost_path = out_path / "cost_analysis.csv"
        m = test_results["metrics"]
        with open(cost_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["cost_component", "amount_inr", "basis"])
            writer.writerow(["False Negative Fraud Loss", m["fn_fraud_loss_inr"], f"{m['false_negatives']} missed fraud txns"])
            writer.writerow(["False Positive Friction Cost", m["fp_friction_cost_inr"], f"{m['false_positives']} legitimate txns flagged @ ₹{self.config.false_positive_cost}/each"])
            writer.writerow(["Review Overhead Cost", m["review_overhead_cost_inr"], f"Manual review @ ₹{self.config.review_cost}/each"])
            writer.writerow(["Total Expected Loss", m["expected_loss_inr"], "FN Loss + FP Cost + Review Cost"])
            writer.writerow(["Fraud Loss Prevented", m["tp_fraud_avoided_inr"], f"{m['true_positives']} fraud txns successfully caught"])
        paths["cost_analysis"] = cost_path

        # 4. report.md
        rep_path = out_path / "report.md"
        with open(rep_path, "w", encoding="utf-8") as f:
            f.write(self._generate_markdown_report(val_tuning, test_results))
        paths["report"] = rep_path

        return paths

    def _generate_markdown_report(self, val_tuning: list[dict], test_results: dict) -> str:
        m = test_results["metrics"]
        split = test_results["split_info"]
        rules = test_results["rule_contributions"]
        arch = test_results["archetype_performance"]

        md = f"""# SentinelRisk — Stage 4: Rules Baseline Evaluation Report

## 1. Executive Summary
The deterministic, rules-only fraud baseline was evaluated on a temporally held-out test set (final 15% chronological split).

- **Precision**: {m['precision_pct']}
- **Recall**: {m['recall_pct']}
- **F1 Score**: {m['f1_score']}
- **Review Rate**: {m['review_rate']}
- **Expected Financial Loss**: INR {m['expected_loss_inr']:,}
- **Fraud Loss Avoided**: INR {m['tp_fraud_avoided_inr']:,}

---

## 2. Chronological Split Setup
- **Train Period (70%)**: {split['train']['start_date']} to {split['train']['end_date']} ({split['train']['count']:,} txns, {split['train']['fraud_count']} fraud, {split['train']['fraud_prevalence']})
- **Validation Period (15%)**: {split['validation']['start_date']} to {split['validation']['end_date']} ({split['validation']['count']:,} txns, {split['validation']['fraud_count']} fraud, {split['validation']['fraud_prevalence']})
- **Held-Out Test Period (15%)**: {split['test']['start_date']} to {split['test']['end_date']} ({split['test']['count']:,} txns, {split['test']['fraud_count']} fraud, {split['test']['fraud_prevalence']})

---

## 3. Confusion Matrix (Held-Out Test Set)

```
                 Actual
              Legitimate       Fraud
Predicted
Legitimate    TN: {m['true_negatives']:<10} FN: {m['false_negatives']:<10}
Fraud         FP: {m['false_positives']:<10} TP: {m['true_positives']:<10}
```

---

## 4. Rule Trigger Contribution Analysis

| Rule Name | Trigger Count | Trigger Rate | True Positives Caught | Rule Precision |
|---|---|---|---|---|
"""
        for r in rules:
            md += f"| {r['display_name']} | {r['trigger_count']} | {r['trigger_rate']} | {r['true_positives']} | {r['precision_when_triggered']} |\n"

        md += f"""
---

## 5. Fraud Archetype Breakdown (Test Set)

| Fraud Archetype | Total Cases | Caught Cases | Missed Cases | Recall |
|---|---|---|---|---|
| Account Takeover (ATO) | {arch['account_takeover']['total_cases']} | {arch['account_takeover']['caught_cases']} | {arch['account_takeover']['missed_cases']} | {arch['account_takeover']['recall']} |
| Card Testing Velocity | {arch['card_testing']['total_cases']} | {arch['card_testing']['caught_cases']} | {arch['card_testing']['missed_cases']} | {arch['card_testing']['recall']} |
| Coordinated Abuse Rings | {arch['coordinated_ring']['total_cases']} | {arch['coordinated_ring']['caught_cases']} | {arch['coordinated_ring']['missed_cases']} | {arch['coordinated_ring']['recall']} |

---

## 6. Business Cost Analysis
- **False Negative Fraud Loss**: INR {m['fn_fraud_loss_inr']:,} ({m['false_negatives']} missed fraud events)
- **False Positive Friction Cost**: INR {m['fp_friction_cost_inr']:,} ({m['false_positives']} legitimate users impacted @ INR {self.config.false_positive_cost}/each)
- **Manual Review Overhead**: INR {m['review_overhead_cost_inr']:,}
- **Total Expected Loss**: **INR {m['expected_loss_inr']:,}**
- **Fraud Prevented (Benefit)**: **INR {m['tp_fraud_avoided_inr']:,}**
"""
        return md

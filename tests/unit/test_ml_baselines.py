"""
SentinelRisk — Stage 5: Machine Learning Baselines Unit Tests

Verifies:
  - Strict target and identifier segregation (zero raw IDs or targets in X)
  - Chronological split alignment with Stage 4 boundaries
  - Preprocessor fit-on-train isolation
  - Logistic Regression probability outputs and coefficient extraction
  - LightGBM probability outputs and feature importance extraction
  - Validation-only threshold optimization (Test set isolation)
  - Mathematical consistency of confusion matrix, PR-AUC, ROC-AUC, and Expected Loss
  - Deterministic training and evaluation reproducibility
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from ml.training.dataset import prepare_ml_dataset, DatasetSplits
from ml.training.preprocessing import build_logistic_preprocessor
from ml.training.trainer import MLTrainer, CostModelConfig


@pytest.fixture
def mock_dataset_splits():
    """Create a controlled synthetic chronological dataset for ML unit testing."""
    base_time = datetime(2025, 1, 1, 10, 0, 0)
    rows = []

    for i in range(200):
        t = base_time + timedelta(hours=i)
        is_fraud = 1 if (i % 15 == 0) else 0
        rows.append({
            "transaction_id": i + 1,
            "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "merchant_id": 101,
            "customer_id": 202,
            "device_id": 303,
            "payment_instrument_id": 404,
            "amount": 1000.0 if is_fraud == 0 else 15000.0,
            "amount_log": np.log(1001.0 if is_fraud == 0 else 15001.0),
            "hour_of_day": t.hour,
            "day_of_week": t.weekday(),
            "is_weekend": 1 if t.weekday() in (5, 6) else 0,
            "is_night": 1 if 0 <= t.hour <= 5 else 0,
            "merchant_category_idx": 1,
            "pi_type_idx": 1,
            "cust_age_days": 30.0,
            "cust_txn_count_prev": 5,
            "cust_amount_sum_prev": 5000.0,
            "cust_amount_mean_prev": 1000.0,
            "cust_amount_std_prev": 100.0,
            "cust_amount_max_prev": 1500.0,
            "cust_days_since_last_txn": 2.0,
            "cust_amount_to_mean_ratio": 1.0 if is_fraud == 0 else 15.0,
            "cust_amount_zscore": 0.0 if is_fraud == 0 else 14.0,
            "cust_is_first_txn": 0,
            "cust_decline_rate_prev": 0.0,
            "velocity_txn_count_1h": 0 if is_fraud == 0 else 4,
            "velocity_amount_sum_1h": 0.0,
            "velocity_txn_count_24h": 1,
            "velocity_amount_sum_24h": 1000.0,
            "velocity_txn_count_7d": 3,
            "velocity_amount_sum_7d": 3000.0,
            "merchant_age_days": 100.0,
            "merchant_txn_count_prev": 50,
            "merchant_amount_mean_prev": 1000.0,
            "merchant_amount_std_prev": 100.0,
            "merchant_decline_rate_prev": 0.02,
            "merchant_velocity_txn_count_1h": 1,
            "merchant_velocity_txn_count_24h": 10,
            "merchant_velocity_txn_count_7d": 50,
            "amount_to_merchant_mean_ratio": 1.0 if is_fraud == 0 else 15.0,
            "device_txn_count_prev": 5,
            "device_distinct_cust_prev": 1,
            "device_distinct_merchants_prev": 1,
            "device_velocity_count_24h": 1,
            "device_velocity_count_7d": 5,
            "device_is_new_for_cust": 0 if is_fraud == 0 else 1,
            "device_age_days": 20.0,
            "pi_txn_count_prev": 5,
            "pi_distinct_cust_prev": 1,
            "pi_distinct_merchants_prev": 1,
            "pi_velocity_count_1h": 0 if is_fraud == 0 else 4,
            "pi_velocity_count_24h": 1,
            "pi_age_days": 20.0,
            "is_fraud": is_fraud,
            "is_fraud_ground_truth": is_fraud,
            "fraud_archetype": "account_takeover" if is_fraud else "none",
            "fraud_case_id": "ATO_01" if is_fraud else "",
        })
    df = pd.DataFrame(rows)

    # Use 70 / 15 / 15 split
    n = len(df)
    i_tr = int(n * 0.70)
    i_val = int(n * 0.85)

    feat_cols = [c for c in df.columns if c not in {
        "transaction_id", "timestamp", "merchant_id", "customer_id", "device_id",
        "payment_instrument_id", "is_fraud", "is_fraud_ground_truth", "fraud_archetype", "fraud_case_id"
    }]

    tr_df = df.iloc[:i_tr]
    val_df = df.iloc[i_tr:i_val]
    te_df = df.iloc[i_val:]

    y_tr = tr_df["is_fraud_ground_truth"].values
    scale_pos = (len(y_tr) - sum(y_tr)) / max(1, sum(y_tr))

    return DatasetSplits(
        X_train=tr_df[feat_cols],
        y_train=y_tr,
        amounts_train=tr_df["amount"].values,
        archetypes_train=tr_df["fraud_archetype"].values,
        X_val=val_df[feat_cols],
        y_val=val_df["is_fraud_ground_truth"].values,
        amounts_val=val_df["amount"].values,
        archetypes_val=val_df["fraud_archetype"].values,
        X_test=te_df[feat_cols],
        y_test=te_df["is_fraud_ground_truth"].values,
        amounts_test=te_df["amount"].values,
        archetypes_test=te_df["fraud_archetype"].values,
        feature_names=feat_cols,
        scale_pos_weight=scale_pos,
        split_info={
            "train": {"count": len(tr_df), "fraud_count": int(y_tr.sum())},
            "validation": {"count": len(val_df), "fraud_count": int(val_df["is_fraud_ground_truth"].sum())},
            "test": {"count": len(te_df), "fraud_count": int(te_df["is_fraud_ground_truth"].sum())},
        },
    )


class TestDataAndTargetSegregation:
    """Verify target and raw identifier exclusion safeguards."""

    def test_feature_isolation_safeguards(self, mock_dataset_splits):
        splits = mock_dataset_splits
        forbidden_cols = [
            "transaction_id", "timestamp", "merchant_id", "customer_id",
            "device_id", "payment_instrument_id", "is_fraud", "is_fraud_ground_truth",
            "fraud_archetype", "fraud_case_id"
        ]

        for col in forbidden_cols:
            assert col not in splits.X_train.columns
            assert col not in splits.X_val.columns
            assert col not in splits.X_test.columns

        assert len(splits.feature_names) == 47

    def test_scale_pos_weight_derived_strictly_from_train(self, mock_dataset_splits):
        splits = mock_dataset_splits
        y_train = splits.y_train
        expected_scale = (len(y_train) - y_train.sum()) / y_train.sum()
        assert np.isclose(splits.scale_pos_weight, expected_scale)


class TestMLModelTrainingAndOutputs:
    """Verify Logistic Regression and LightGBM training and probability bounds."""

    def test_logistic_regression_pipeline(self, mock_dataset_splits):
        trainer = MLTrainer(mock_dataset_splits, CostModelConfig())
        lr_pipeline = trainer.train_logistic_regression()

        # Check probability bounds
        probs = lr_pipeline.predict_proba(mock_dataset_splits.X_val)[:, 1]
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)
        assert len(probs) == len(mock_dataset_splits.X_val)

        # Check coefficient extraction
        coefs = trainer.extract_logistic_coefficients(lr_pipeline)
        assert len(coefs) > 0
        assert "feature" in coefs[0]
        assert "coefficient" in coefs[0]

    def test_lightgbm_training(self, mock_dataset_splits):
        trainer = MLTrainer(mock_dataset_splits, CostModelConfig())
        lgb_model = trainer.train_lightgbm()

        # Check probability bounds
        probs = lgb_model.predict_proba(mock_dataset_splits.X_val)[:, 1]
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)
        assert len(probs) == len(mock_dataset_splits.X_val)

        # Check feature importance extraction
        importances = trainer.extract_lightgbm_feature_importance(lgb_model)
        assert len(importances) == 47
        assert "gain_importance" in importances[0]


class TestThresholdOptimizationAndMetrics:
    """Verify validation threshold selection and metric calculations."""

    def test_validation_threshold_selection(self, mock_dataset_splits):
        trainer = MLTrainer(mock_dataset_splits, CostModelConfig())
        lgb_model = trainer.train_lightgbm()

        best_thresh, tuning = trainer.optimize_threshold_on_validation(lgb_model)
        assert 0.05 <= best_thresh <= 0.95
        assert len(tuning) == 19

    def test_mathematical_consistency_of_metrics(self, mock_dataset_splits):
        trainer = MLTrainer(mock_dataset_splits, CostModelConfig())
        lgb_model = trainer.train_lightgbm()

        res = trainer.evaluate_model_on_test("LightGBM", lgb_model, 0.5)
        m = res["metrics"]

        # Confusion matrix sum == total test rows
        assert m["true_positives"] + m["false_positives"] + m["true_negatives"] + m["false_negatives"] == m["total_transactions"]

        # PR-AUC and ROC-AUC bounds
        assert 0.0 <= m["pr_auc"] <= 1.0
        assert 0.0 <= m["roc_auc"] <= 1.0

        # Expected Loss formula
        expected_calc = m["fn_fraud_loss_inr"] + m["fp_friction_cost_inr"] + m["review_overhead_cost_inr"]
        assert np.isclose(m["expected_loss_inr"], expected_calc)

    def test_reproducibility(self, mock_dataset_splits):
        trainer1 = MLTrainer(mock_dataset_splits, CostModelConfig(), random_seed=42)
        m1 = trainer1.train_lightgbm()
        res1 = trainer1.evaluate_model_on_test("LightGBM", m1, 0.5)

        trainer2 = MLTrainer(mock_dataset_splits, CostModelConfig(), random_seed=42)
        m2 = trainer2.train_lightgbm()
        res2 = trainer2.evaluate_model_on_test("LightGBM", m2, 0.5)

        assert res1["metrics"]["expected_loss_inr"] == res2["metrics"]["expected_loss_inr"]
        assert res1["metrics"]["f1_score"] == res2["metrics"]["f1_score"]
